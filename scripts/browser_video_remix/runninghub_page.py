import json
import re
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .browser_executor import (
    ClipExecutionRequest,
    RunningHubDownloadResult,
    RunningHubPollResult,
    RunningHubSubmitResult,
    RunningHubTaskStatus,
)
from .live_state import PauseReason
from .workflow_binding import WorkflowBinding, inspect_workflow_binding, load_workflow_binding


class RunningHubPageAdapter:
    VIDEO_INPUT_SELECTORS = ("#video-upload", "input[type='file'][accept*='video']")
    IMAGE_INPUT_SELECTORS = ("#image-upload", "input[type='file'][accept*='image']")
    WIDTH_INPUT_SELECTORS = ("input[name='width']", "#width")
    HEIGHT_INPUT_SELECTORS = ("input[name='height']", "#height")
    SUBMIT_BUTTON_SELECTORS = ("button[data-testid='submit-workflow']", "button")
    TASK_ID_SELECTORS = ("[data-testid='task-id']", "[data-task-id]")
    TASK_STATUS_SELECTORS = ("[data-testid='task-status']", "[data-task-status]")
    DOWNLOAD_BUTTON_SELECTORS = ("button[data-testid='download-render']", "a[download]")
    LOGIN_BUTTON_TEXTS = ("登录", "登 录", "Log in")
    GRAPH_WORKFLOW_CONTENT_TYPE = "0"
    GRAPH_PROMPT_NUMBER = 0
    GRAPH_REFERENCE_IMAGE_NODE_ID = 57
    GRAPH_SOURCE_VIDEO_NODE_ID = 63
    COMFYUI_FRAME_URL_TOKEN = "comfyUI.html"
    COMFY_FILE_INPUT_SELECTOR = "#comfy-file-input"
    CODEX_UPLOAD_INPUT_SELECTOR = "#codex-upload-input"
    GRAPH_READY_ATTEMPTS = 10
    GRAPH_READY_WAIT_MS = 1000
    GRAPH_LOAD_READY_TIMEOUT_MS = 15000
    GRAPH_QUEUE_RESPONSE_TIMEOUT_MS = 8000
    GRAPH_QUEUE_RESPONSE_WAIT_MS = 3000
    TASK_LIST_READY_ATTEMPTS = 5
    RUNNINGHUB_REQUEST_TIMEOUT_SECONDS = 20
    RUNNINGHUB_DOWNLOAD_TIMEOUT_SECONDS = 60

    def __init__(self, workflow_url: str) -> None:
        self.workflow_url = workflow_url

    def ensure_session(self, page: object) -> RunningHubSubmitResult:
        page.goto(self.workflow_url, wait_until="domcontentloaded")
        if self._is_login_required(page):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return RunningHubSubmitResult(
            status="ready",
            task_id=None,
            pause_reason=None,
        )

    def submit_render_job(
        self,
        page: object,
        request: ClipExecutionRequest,
    ) -> RunningHubSubmitResult:
        session_result = self.ensure_session(page)
        if session_result.pause_reason is not None:
            return session_result

        graph_result = self._submit_render_job_via_graph(page, request)
        if graph_result is not None:
            return graph_result

        video_input = self._find_first_available_locator(
            page,
            self.VIDEO_INPUT_SELECTORS,
            require_visible=False,
        )
        image_input = self._find_first_available_locator(
            page,
            self.IMAGE_INPUT_SELECTORS,
            require_visible=False,
        )
        width_input = self._find_first_available_locator(
            page,
            self.WIDTH_INPUT_SELECTORS,
            require_visible=True,
        )
        height_input = self._find_first_available_locator(
            page,
            self.HEIGHT_INPUT_SELECTORS,
            require_visible=True,
        )
        submit_button = self._find_first_available_locator(
            page,
            self.SUBMIT_BUTTON_SELECTORS,
            require_visible=True,
        )
        if None in {video_input, image_input, width_input, height_input, submit_button}:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )

        video_input.set_input_files(request.clip_path.as_posix())
        image_input.set_input_files(request.reference_image_path.as_posix())
        width_input.fill(str(request.width))
        height_input.fill(str(request.height))
        submit_button.click()

        task_id = self._extract_task_id(page)
        if not task_id:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.MANUAL_CONFIRMATION_REQUIRED,
            )
        return RunningHubSubmitResult(
            status="submitted",
            task_id=task_id,
            pause_reason=None,
        )

    def poll_render_status(self, page: object, task_id: str) -> RunningHubPollResult:
        status = self._normalize_task_status(self._read_task_status_text(page, task_id))
        if status in {RunningHubTaskStatus.DONE, RunningHubTaskStatus.FAILED}:
            return RunningHubPollResult(status, task_id, None)

        task_record = self._find_task_record(page, task_id)
        if task_record is not None:
            status = self._normalize_task_status(
                task_record.get("taskStatus") or task_record.get("status")
            )
        return RunningHubPollResult(status, task_id, None)

    def download_render_output(
        self,
        page: object,
        output_path: Path,
        task_id: str | None = None,
    ) -> RunningHubDownloadResult:
        download_button = self._find_first_available_locator(
            page,
            self.DOWNLOAD_BUTTON_SELECTORS,
            require_visible=True,
        )
        if download_button is not None and self._download_via_button(
            page,
            download_button,
            output_path,
        ):
            return RunningHubDownloadResult("downloaded", output_path, None)

        media_url = self._read_task_media_url(page, task_id)
        if media_url is None:
            media_url = self._read_output_history_media_url(page, task_id)
        if media_url and self._download_media_url(page, media_url, output_path):
            return RunningHubDownloadResult("downloaded", output_path, None)

        if download_button is None:
            return RunningHubDownloadResult(
                "paused",
                None,
                PauseReason.SELECTOR_MISSING,
            )
        return RunningHubDownloadResult(
            "failed",
            None,
            PauseReason.MANUAL_CONFIRMATION_REQUIRED,
        )

    def capture_failure_snapshot(
        self,
        page: object,
        screenshot_path: Path,
        html_path: Path,
        summary_path: Path,
    ) -> None:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        screenshotter = getattr(page, "screenshot", None)
        if callable(screenshotter):
            screenshotter(path=screenshot_path.as_posix(), full_page=True)
        else:
            screenshot_path.write_bytes(b"")

        content_getter = getattr(page, "content", None)
        html = content_getter() if callable(content_getter) else ""
        html_path.write_text(str(html), encoding="utf-8")

        title_getter = getattr(page, "title", None)
        title = title_getter() if callable(title_getter) else ""
        summary_path.write_text(
            json.dumps(
                {
                    "url": str(getattr(page, "url", "")),
                    "title": str(title),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _normalize_task_status(self, status_text: object) -> RunningHubTaskStatus:
        normalized = str(status_text or "").strip().lower()
        if not normalized:
            return RunningHubTaskStatus.PENDING

        done_tokens = ("done", "success", "succeeded", "completed", "complete", "成功", "已完成")
        failed_tokens = ("failed", "error", "失败")
        running_tokens = ("running", "processing", "执行", "运行")
        pending_tokens = ("pending", "queued", "queue", "waiting", "排队", "等待")

        if any(token in normalized for token in done_tokens):
            return RunningHubTaskStatus.DONE
        if any(token in normalized for token in failed_tokens):
            return RunningHubTaskStatus.FAILED
        if any(token in normalized for token in running_tokens):
            return RunningHubTaskStatus.RUNNING
        if any(token in normalized for token in pending_tokens):
            return RunningHubTaskStatus.PENDING
        return RunningHubTaskStatus.PENDING

    def _find_task_record(self, page: object, task_id: str) -> dict[str, object] | None:
        for attempt in range(self.TASK_LIST_READY_ATTEMPTS):
            for record in self._fetch_runninghub_task_list(page):
                if not isinstance(record, dict):
                    continue
                record_task_id = record.get("taskId") or record.get("task_id")
                if str(record_task_id or "").strip() == task_id:
                    return record
            if attempt + 1 < self.TASK_LIST_READY_ATTEMPTS:
                self._wait_for_timeout(page, self.GRAPH_READY_WAIT_MS)
        return None

    def _fetch_runninghub_task_list(self, page: object) -> list[dict[str, object]]:
        fetcher = getattr(page, "fetch_runninghub_task_list", None)
        if callable(fetcher):
            records = fetcher()
            if isinstance(records, list):
                return [record for record in records if isinstance(record, dict)]
            return []

        authorization = self._read_runninghub_authorization(page)
        identify = self._read_runninghub_identify(page)
        if not authorization or not identify:
            return []

        access_key = self._fetch_runninghub_access_key(authorization)
        if not access_key:
            return []

        payload = self._post_runninghub_json(
            url=(
                f"{self._runninghub_origin()}/task/list"
                f"?Rh-Comfy-Auth={quote(access_key)}"
                f"&Rh-Identify={quote(identify)}"
            ),
            authorization=authorization,
            body={
                "size": 20,
                "current": 1,
                "taskStatus": ["RUNNING", "QUEUED", "SUCCESS", "FAILED"],
                "taskType": ["WORKFLOW", "WEBAPP"],
            },
        )
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, dict):
            return []
        records = data.get("records")
        if not isinstance(records, list):
            return []
        return [record for record in records if isinstance(record, dict)]

    def _read_runninghub_authorization(self, page: object) -> str | None:
        reader = getattr(page, "read_runninghub_authorization", None)
        if callable(reader):
            authorization = reader()
            if authorization:
                return str(authorization).strip()

        evaluator = getattr(page, "evaluate", None)
        if not callable(evaluator):
            return None

        try:
            authorization = evaluator(
                """
                () => {
                    const exactKeys = [
                        'authorization',
                        'Authorization',
                        'Rh-Accesstoken',
                        'rh-access-token',
                        'accessToken',
                        'token',
                    ];
                    const storages = [window.localStorage, window.sessionStorage];
                    const seen = new Set();
                    const candidates = [];
                    const add = (value) => {
                        if (typeof value !== 'string') {
                            return;
                        }
                        const trimmed = value.trim();
                        if (!trimmed || seen.has(trimmed)) {
                            return;
                        }
                        seen.add(trimmed);
                        candidates.push(trimmed);
                    };
                    const scanObject = (value) => {
                        if (!value || typeof value !== 'object') {
                            return;
                        }
                        for (const [key, nested] of Object.entries(value)) {
                            if (typeof nested === 'string' && /token|auth/i.test(key)) {
                                add(nested);
                            }
                        }
                    };
                    for (const storage of storages) {
                        for (const key of exactKeys) {
                            const value = storage.getItem(key);
                            if (value) {
                                add(value);
                            }
                        }
                        for (let index = 0; index < storage.length; index += 1) {
                            const key = storage.key(index) ?? '';
                            const value = storage.getItem(key);
                            if (!value) {
                                continue;
                            }
                            if (/token|auth/i.test(key)) {
                                add(value);
                            }
                            try {
                                scanObject(JSON.parse(value));
                            } catch (error) {
                                // ignore non-JSON values
                            }
                        }
                    }
                    const raw = candidates.find((value) => /^Bearer\\s+/i.test(value))
                        ?? candidates[0]
                        ?? null;
                    if (typeof raw !== 'string' || !raw.trim()) {
                        return null;
                    }
                    return /^Bearer\\s+/i.test(raw) ? raw : `Bearer ${raw}`;
                }
                """
            )
        except Exception:
            return None

        if not isinstance(authorization, str):
            return None
        authorization = authorization.strip()
        return authorization or None

    def _read_runninghub_identify(self, page: object) -> str | None:
        reader = getattr(page, "read_runninghub_identify", None)
        if callable(reader):
            identify = reader()
            if isinstance(identify, str) and identify.strip():
                return identify.strip()

        for source in (
            str(getattr(page, "url", "")),
            self._read_page_content(page),
            self._evaluate_runninghub_identify(page),
        ):
            identify = self._extract_identify_from_text(source)
            if identify:
                return identify
        return None

    def _evaluate_runninghub_identify(self, page: object) -> str:
        evaluator = getattr(page, "evaluate", None)
        if not callable(evaluator):
            return ""
        try:
            result = evaluator(
                """
                () => {
                    const storages = [window.localStorage, window.sessionStorage];
                    const candidates = [];
                    const add = (value) => {
                        if (typeof value !== 'string') {
                            return;
                        }
                        const trimmed = value.trim();
                        if (/^[a-f0-9]{32}$/i.test(trimmed)) {
                            candidates.push(trimmed);
                        }
                    };
                    add(new URL(window.location.href).searchParams.get('identify'));
                    add(new URL(window.location.href).searchParams.get('Rh-Identify'));
                    for (const storage of storages) {
                        for (let index = 0; index < storage.length; index += 1) {
                            const key = storage.key(index) ?? '';
                            const value = storage.getItem(key);
                            if (!value) {
                                continue;
                            }
                            if (/identify/i.test(key)) {
                                add(value);
                            }
                            try {
                                const parsed = JSON.parse(value);
                                if (parsed && typeof parsed === 'object') {
                                    for (const [nestedKey, nestedValue] of Object.entries(parsed)) {
                                        if (/identify/i.test(nestedKey) && typeof nestedValue === 'string') {
                                            add(nestedValue);
                                        }
                                    }
                                }
                            } catch (error) {
                                // ignore non-JSON values
                            }
                        }
                    }
                    return candidates.join(' ');
                }
                """
            )
        except Exception:
            return ""
        return str(result or "")

    def _extract_identify_from_text(self, text: object) -> str | None:
        if not isinstance(text, str):
            return None
        for pattern in (
            r"(?:Rh-Identify|identify)=([a-f0-9]{32})",
            r"rh-images\.xiaoyaoyou\.com/([a-f0-9]{32})/",
            r"\b([a-f0-9]{32})\b",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match is not None:
                return match.group(1)
        return None

    def _fetch_runninghub_access_key(self, authorization: str) -> str | None:
        payload = self._post_runninghub_json(
            url=f"{self._runninghub_origin()}/api/instance/access/auth",
            authorization=authorization,
            body={},
        )
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        access_key = data.get("accessKey") or data.get("access_key")
        if not isinstance(access_key, str):
            return None
        access_key = access_key.strip()
        return access_key or None

    def _post_runninghub_json(
        self,
        *,
        url: str,
        authorization: str,
        body: dict[str, object],
    ) -> dict[str, object] | None:
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "authorization": authorization,
            },
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self.RUNNINGHUB_REQUEST_TIMEOUT_SECONDS,
            ) as response:
                payload = response.read().decode("utf-8")
        except Exception:
            return None
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _download_via_button(
        self,
        page: object,
        download_button: object,
        output_path: Path,
    ) -> bool:
        expect_download = getattr(page, "expect_download", None)
        if not callable(expect_download):
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with expect_download() as pending_download:
            download_button.click()
        pending_download.value.save_as(output_path.as_posix())
        return self._output_file_ready(output_path)

    def _read_task_media_url(self, page: object, task_id: str | None) -> str | None:
        if not task_id:
            return None

        reader = getattr(page, "read_task_media_url", None)
        evaluator = getattr(page, "evaluate", None)
        for attempt in range(self.TASK_LIST_READY_ATTEMPTS):
            media_url: object = None
            if callable(reader):
                media_url = reader(task_id)
            elif callable(evaluator):
                try:
                    media_url = evaluator(
                        """
                        (taskId) => {
                            const extractUrl = (root) => {
                                if (!root) {
                                    return null;
                                }
                                const candidates = [
                                    ...root.querySelectorAll('video[src], video source[src], a[href], img[src]')
                                ];
                                for (const candidate of candidates) {
                                    const url =
                                        candidate.currentSrc ??
                                        candidate.src ??
                                        candidate.href ??
                                        '';
                                    if (typeof url === 'string' && /^https?:\\/\\//i.test(url)) {
                                        return url;
                                    }
                                }
                                return null;
                            };
                            for (const element of document.querySelectorAll('*')) {
                                const text = String(element.textContent ?? '').trim();
                                if (!text.includes(taskId)) {
                                    continue;
                                }
                                const container =
                                    element.closest('[data-task-id], article, li, section, div') ??
                                    element;
                                const mediaUrl =
                                    extractUrl(container) ??
                                    extractUrl(container.parentElement) ??
                                    extractUrl(container.parentElement?.parentElement ?? null);
                                if (mediaUrl) {
                                    return mediaUrl;
                                }
                            }
                            return null;
                        }
                        """,
                        task_id,
                    )
                except Exception:
                    media_url = None
            if isinstance(media_url, str) and media_url.strip():
                return media_url.strip()
            if attempt + 1 < self.TASK_LIST_READY_ATTEMPTS:
                self._wait_for_timeout(page, self.GRAPH_READY_WAIT_MS)
        return None

    def _download_media_url(self, page: object, media_url: str, output_path: Path) -> bool:
        downloader = getattr(page, "download_url_to_path", None)
        if callable(downloader):
            downloader(media_url, output_path.as_posix())
            return self._output_file_ready(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        request = Request(
            media_url,
            headers={"user-agent": "Mozilla/5.0"},
            method="GET",
        )
        try:
            with urlopen(
                request,
                timeout=self.RUNNINGHUB_DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                output_path.write_bytes(response.read())
        except Exception:
            return False
        return self._output_file_ready(output_path)

    def _read_output_history_media_url(self, page: object, task_id: str | None) -> str | None:
        if not task_id:
            return None

        workflow_id = self._extract_workflow_id(self.workflow_url)
        for attempt in range(self.TASK_LIST_READY_ATTEMPTS):
            for record in self._fetch_runninghub_output_history(page):
                if not isinstance(record, dict):
                    continue
                record_task_id = str(record.get("taskId") or record.get("task_id") or "").strip()
                if record_task_id != task_id:
                    continue
                record_workflow_id = str(record.get("workflowId") or "").strip()
                if workflow_id and record_workflow_id and record_workflow_id != workflow_id:
                    continue
                for key in ("fileUrl", "filePreviewUrl"):
                    media_url = record.get(key)
                    if isinstance(media_url, str) and media_url.strip():
                        return media_url.strip()
            if attempt + 1 < self.TASK_LIST_READY_ATTEMPTS:
                self._wait_for_timeout(page, self.GRAPH_READY_WAIT_MS)
        return None

    def _fetch_runninghub_output_history(self, page: object) -> list[dict[str, object]]:
        fetcher = getattr(page, "fetch_runninghub_output_history", None)
        if callable(fetcher):
            records = fetcher()
            if isinstance(records, list):
                return [record for record in records if isinstance(record, dict)]
            return []

        authorization = self._read_runninghub_authorization(page)
        if not authorization:
            return []

        payload = self._post_runninghub_json(
            url=f"{self._runninghub_origin()}/api/output/v2/history",
            authorization=authorization,
            body={
                "size": 50,
                "current": 1,
                "taskType": ["WORKFLOW", "WEBAPP"],
                "fromId": "",
            },
        )
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, list):
            return []
        return [record for record in data if isinstance(record, dict)]

    def _output_file_ready(self, output_path: Path) -> bool:
        return output_path.exists() and output_path.stat().st_size > 0

    def _read_page_content(self, page: object) -> str:
        content_getter = getattr(page, "content", None)
        if not callable(content_getter):
            return ""
        try:
            return str(content_getter())
        except Exception:
            return ""

    def _runninghub_origin(self) -> str:
        parsed = urlsplit(self.workflow_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _submit_render_job_via_graph(
        self,
        page: object,
        request: ClipExecutionRequest,
    ) -> RunningHubSubmitResult | None:
        workflow_id = self._extract_workflow_id(self.workflow_url)
        if workflow_id is None:
            return None

        workflow = None
        login_required_without_cache = False
        graph_loader_ready = self._page_has_graph_loader(page)
        for attempt in range(self.GRAPH_READY_ATTEMPTS):
            workflow_status, workflow = self._fetch_workflow_content(page, workflow_id)
            if workflow_status == "login_required":
                workflow = self._read_cached_workflow_content(page, workflow_id)
                login_required_without_cache = workflow is None
            graph_loader_ready = graph_loader_ready or self._page_has_graph_loader(page)
            if workflow is not None and graph_loader_ready:
                break
            if attempt + 1 < self.GRAPH_READY_ATTEMPTS:
                self._wait_for_timeout(page, self.GRAPH_READY_WAIT_MS)

        if login_required_without_cache and workflow is None:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        if workflow is None:
            return None
        if not graph_loader_ready:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )
        binding = self._resolve_workflow_binding(workflow, request, workflow_id)
        workflow = self._apply_graph_request_overrides(workflow, request, binding)

        if not self._load_graph_data(page, workflow):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )

        if not self._upload_graph_asset(
            page,
            self._binding_video_node_id(binding),
            request.clip_path,
        ):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )

        for node_id, reference_path in self._build_reference_uploads(request, binding):
            if not self._upload_graph_asset(
                page,
                node_id,
                reference_path,
            ):
                return RunningHubSubmitResult(
                    status="paused",
                    task_id=None,
                    pause_reason=PauseReason.SELECTOR_MISSING,
                )

        task_id = self._queue_graph_prompt(page, self.GRAPH_PROMPT_NUMBER)
        if not task_id:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.MANUAL_CONFIRMATION_REQUIRED,
            )

        return RunningHubSubmitResult(
            status="submitted",
            task_id=task_id,
            pause_reason=None,
        )

    def _fetch_workflow_content(
        self,
        page: object,
        workflow_id: str,
    ) -> tuple[str, dict[str, object] | None]:
        fetcher = getattr(page, "fetch_workflow_content", None)
        if callable(fetcher):
            return self._parse_workflow_content_response(
                fetcher(workflow_id, self.GRAPH_WORKFLOW_CONTENT_TYPE)
            )

        evaluator = getattr(page, "evaluate", None)
        if not callable(evaluator):
            return ("unsupported", None)

        return self._parse_workflow_content_response(
            evaluator(
                """
                async ({ workflowId, contentType }) => {
                    const response = await fetch("/api/workflow/getContent", {
                        method: "POST",
                        headers: { "content-type": "application/json" },
                        body: JSON.stringify({ workflowId, contentType }),
                    });
                    const text = await response.text();
                    try {
                        return JSON.parse(text);
                    } catch (error) {
                        return {
                            ok: response.ok,
                            status: response.status,
                            text,
                        };
                    }
                }
                """,
                {
                    "workflowId": workflow_id,
                    "contentType": self.GRAPH_WORKFLOW_CONTENT_TYPE,
                },
            )
        )

    def _parse_workflow_content_response(
        self,
        workflow_response: object,
    ) -> tuple[str, dict[str, object] | None]:
        if workflow_response is None:
            return ("unsupported", None)

        if isinstance(workflow_response, dict):
            status_code = workflow_response.get("status")
            message = str(workflow_response.get("msg", "")).upper()
            body_text = str(workflow_response.get("text", "")).upper()
            if status_code in {401, 403, 412} or "TOKEN_INVALID" in message or "TOKEN_INVALID" in body_text:
                return ("login_required", None)

            response_data = workflow_response.get("data")
            if isinstance(response_data, dict) and "workflowContent" in response_data:
                workflow = self._normalize_workflow_content(
                    response_data.get("workflowContent")
                )
                if workflow is not None:
                    return ("ready", workflow)

        workflow = self._normalize_workflow_content(workflow_response)
        if workflow is None or "nodes" not in workflow:
            return ("unsupported", None)
        return ("ready", workflow)

    def _read_cached_workflow_content(self, page: object, workflow_id: str) -> dict[str, object] | None:
        reader = getattr(page, "read_cached_workflow_content", None)
        if callable(reader):
            return self._normalize_workflow_content(reader(workflow_id))

        evaluator = getattr(page, "evaluate", None)
        if not callable(evaluator):
            return None

        return self._normalize_workflow_content(
            evaluator(
                """
                (workflowId) => {
                    const directKey = `iframe${workflowId}`;
                    const directValue = window.sessionStorage.getItem(directKey);
                    if (directValue) {
                        return directValue;
                    }

                    for (let index = 0; index < window.sessionStorage.length; index += 1) {
                        const key = window.sessionStorage.key(index) ?? "";
                        if (!key.startsWith("iframe") || !key.includes(workflowId)) {
                            continue;
                        }
                        const value = window.sessionStorage.getItem(key);
                        if (value) {
                            return value;
                        }
                    }
                    return null;
                }
                """,
                workflow_id,
            )
        )

    def _normalize_workflow_content(self, workflow_content: object) -> dict[str, object] | None:
        if workflow_content is None:
            return None
        if isinstance(workflow_content, str):
            try:
                workflow_content = json.loads(workflow_content)
            except json.JSONDecodeError:
                return None
        if not isinstance(workflow_content, dict):
            return None
        return workflow_content

    def _apply_graph_request_overrides(
        self,
        workflow: dict[str, object],
        request: ClipExecutionRequest,
        binding: WorkflowBinding | None = None,
    ) -> dict[str, object]:
        workflow_copy = json.loads(json.dumps(workflow))
        nodes = workflow_copy.get("nodes")
        if not isinstance(nodes, list):
            return workflow_copy

        video_node_id = self._binding_video_node_id(binding)
        for node in nodes:
            if not isinstance(node, dict):
                continue
            widgets_values = node.get("widgets_values")
            if node.get("id") == video_node_id and isinstance(widgets_values, dict):
                if "custom_width" in widgets_values:
                    widgets_values["custom_width"] = request.width
                if "custom_height" in widgets_values:
                    widgets_values["custom_height"] = request.height
            if binding is not None:
                self._apply_lora_control_override(
                    node=node,
                    request=request,
                    optional_controls=binding.optional_controls,
                )
        return workflow_copy

    def _resolve_workflow_binding(
        self,
        workflow: dict[str, object],
        request: ClipExecutionRequest,
        workflow_id: str,
    ) -> WorkflowBinding | None:
        if request.workflow_binding_path is not None and request.workflow_binding_path.exists():
            return load_workflow_binding(request.workflow_binding_path)

        binding = inspect_workflow_binding(workflow)
        if not binding.workflow_id:
            return WorkflowBinding(
                workflow_id=workflow_id,
                video_node_id=binding.video_node_id,
                reference_node_ids=binding.reference_node_ids,
                optional_controls=binding.optional_controls,
            )
        return binding

    def _binding_video_node_id(self, binding: WorkflowBinding | None) -> int:
        if binding is None or binding.video_node_id is None:
            return self.GRAPH_SOURCE_VIDEO_NODE_ID
        return binding.video_node_id

    def _build_reference_uploads(
        self,
        request: ClipExecutionRequest,
        binding: WorkflowBinding | None,
    ) -> list[tuple[int, Path]]:
        reference_paths = list(request.person_reference_images.values())
        if not reference_paths:
            reference_paths = [request.reference_image_path]

        node_ids = (
            list(binding.reference_node_ids)
            if binding is not None and binding.reference_node_ids
            else [self.GRAPH_REFERENCE_IMAGE_NODE_ID]
        )
        if not node_ids:
            return []

        uploads: list[tuple[int, Path]] = []
        for index, reference_path in enumerate(reference_paths):
            node_id = node_ids[min(index, len(node_ids) - 1)]
            uploads.append((node_id, reference_path))
        return uploads

    def _apply_lora_control_override(
        self,
        *,
        node: dict[str, object],
        request: ClipExecutionRequest,
        optional_controls: dict[str, int],
    ) -> None:
        node_id = node.get("id")
        if not isinstance(node_id, int):
            return

        widgets_values = node.get("widgets_values")
        if not isinstance(widgets_values, dict):
            return

        for lora_name, lora_weight in request.lora_controls.items():
            expected_keys = {lora_name, f"lora:{lora_name}"}
            if not any(
                control_key in expected_keys and control_node_id == node_id
                for control_key, control_node_id in optional_controls.items()
            ):
                continue
            if "strength_model" in widgets_values:
                widgets_values["strength_model"] = lora_weight
            if "strength_clip" in widgets_values:
                widgets_values["strength_clip"] = lora_weight
            if "weight" in widgets_values:
                widgets_values["weight"] = lora_weight
            if "lora_weight" in widgets_values:
                widgets_values["lora_weight"] = lora_weight

    def _load_graph_data(self, page: object, workflow: dict[str, object]) -> bool:
        loader = getattr(page, "load_graph_data", None)
        if callable(loader):
            loader(workflow)
            return True

        frame = self._find_comfyui_frame(page)
        if frame is None:
            return False

        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator):
            return False

        try:
            loaded = bool(
                evaluator(
                    """
                    async (workflow) => {
                        const app = globalThis.app;
                        if (!app || typeof app.loadGraphData !== "function") {
                            return false;
                        }
                        await app.loadGraphData(workflow, true, true, "");
                        return true;
                    }
                    """,
                    workflow,
                )
            )
            if not loaded:
                return False

            node_ids = self._extract_workflow_node_ids(workflow)
            wait_for_function = getattr(frame, "wait_for_function", None)
            if callable(wait_for_function) and node_ids:
                wait_for_function(
                    """
                    ({ nodeIds }) => {
                        const graph = globalThis.app?.graph;
                        const nodes = graph?._nodes ?? graph?.nodes;
                        if (!graph || !Array.isArray(nodes) || nodes.length === 0) {
                            return false;
                        }
                        return nodeIds.every((nodeId) => Boolean(
                            graph.getNodeById?.(nodeId) ??
                            nodes.find((candidate) => candidate?.id === nodeId)
                        ));
                    }
                    """,
                    arg={"nodeIds": node_ids},
                    timeout=self.GRAPH_LOAD_READY_TIMEOUT_MS,
                )
            return True
        except Exception:
            return False

    def _upload_graph_asset(self, page: object, node_id: int, file_path: Path) -> bool:
        uploader = getattr(page, "upload_graph_asset", None)
        if callable(uploader):
            return bool(uploader(node_id, file_path.as_posix()))

        frame = self._find_comfyui_frame(page)
        if frame is None:
            return False

        evaluator = getattr(frame, "evaluate", None)
        locator_factory = getattr(frame, "locator", None)
        if not callable(evaluator) or not callable(locator_factory):
            return False

        try:
            upload_ready = False
            for attempt in range(self.GRAPH_READY_ATTEMPTS):
                upload_ready = bool(
                    evaluator(
                        """
                        ({ nodeId }) => {
                            const app = globalThis.app;
                            const graph = app?.graph;
                            if (!graph) {
                                return false;
                            }
                            const node =
                                graph.getNodeById?.(nodeId) ??
                                graph._nodes?.find((candidate) => candidate?.id === nodeId);
                            if (!node || !Array.isArray(node.widgets)) {
                                return false;
                            }
                            const uploadWidget = node.widgets.find((widget) => {
                                if (!widget || typeof widget.callback !== "function") {
                                    return false;
                                }
                                const name = String(widget.name ?? "").toLowerCase();
                                return name === "upload" || name.includes("upload");
                            });
                            if (!uploadWidget) {
                                return false;
                            }
                            uploadWidget.callback();
                            return true;
                        }
                        """,
                        {"nodeId": node_id},
                    )
                )
                if upload_ready:
                    break
                if attempt + 1 < self.GRAPH_READY_ATTEMPTS:
                    self._wait_for_timeout(page, self.GRAPH_READY_WAIT_MS)
            if not upload_ready:
                return False

            file_input = locator_factory(self.COMFY_FILE_INPUT_SELECTOR)
            set_input_files = getattr(file_input, "set_input_files", None)
            if not callable(set_input_files):
                return False
            previous_values = self._read_graph_node_values(frame, node_id)
            set_input_files(file_path.as_posix())

            wait_for_function = getattr(frame, "wait_for_function", None)
            if callable(wait_for_function):
                wait_for_function(
                    """
                    ({ nodeId, previousValues }) => {
                        const collectValues = (node) => {
                            const values = [];
                            for (const widget of node.widgets ?? []) {
                                const value = widget?.value;
                                if (typeof value === "string") {
                                    values.push(value);
                                    continue;
                                }
                                if (value && typeof value === "object") {
                                    values.push(JSON.stringify(value));
                                }
                            }

                            const widgetValues = node.widgets_values;
                            if (typeof widgetValues === "string") {
                                values.push(widgetValues);
                            } else if (Array.isArray(widgetValues)) {
                                for (const value of widgetValues) {
                                    if (typeof value === "string") {
                                        values.push(value);
                                    }
                                }
                            } else if (widgetValues && typeof widgetValues === "object") {
                                for (const value of Object.values(widgetValues)) {
                                    if (typeof value === "string") {
                                        values.push(value);
                                    }
                                }
                            }
                            return values;
                        };

                        const app = globalThis.app;
                        const graph = app?.graph;
                        const node =
                            graph?.getNodeById?.(nodeId) ??
                            graph?._nodes?.find((candidate) => candidate?.id === nodeId);
                        if (!node) {
                            return false;
                        }

                        const currentValues = collectValues(node);
                        if (!Array.isArray(previousValues) || previousValues.length === 0) {
                            return currentValues.length > 0;
                        }
                        return currentValues.some((value) => !previousValues.includes(value));
                    }
                    """,
                    arg={"nodeId": node_id, "previousValues": previous_values},
                    timeout=15000,
                )

            return True
        except Exception:
            pass

        return self._upload_graph_asset_via_api(frame, locator_factory, node_id, file_path)

    def _read_graph_node_values(self, frame: object, node_id: int) -> list[str]:
        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator):
            return []

        values = evaluator(
            """
            ({ nodeId }) => {
                const graph = globalThis.app?.graph;
                const node =
                    graph?.getNodeById?.(nodeId) ??
                    graph?._nodes?.find((candidate) => candidate?.id === nodeId);
                if (!node) {
                    return [];
                }

                const collected = [];
                for (const widget of node.widgets ?? []) {
                    const value = widget?.value;
                    if (typeof value === "string") {
                        collected.push(value);
                        continue;
                    }
                    if (value && typeof value === "object") {
                        collected.push(JSON.stringify(value));
                    }
                }

                const widgetValues = node.widgets_values;
                if (typeof widgetValues === "string") {
                    collected.push(widgetValues);
                } else if (Array.isArray(widgetValues)) {
                    for (const value of widgetValues) {
                        if (typeof value === "string") {
                            collected.push(value);
                        }
                    }
                } else if (widgetValues && typeof widgetValues === "object") {
                    for (const value of Object.values(widgetValues)) {
                        if (typeof value === "string") {
                            collected.push(value);
                        }
                    }
                }
                return collected;
            }
            """,
            {"nodeId": node_id},
        )
        if not isinstance(values, list):
            return []
        return [str(value) for value in values]

    def _upload_graph_asset_via_api(
        self,
        frame: object,
        locator_factory: object,
        node_id: int,
        file_path: Path,
    ) -> bool:
        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator) or not callable(locator_factory):
            return False

        try:
            evaluator(
                f"""
                () => {{
                    let input = document.querySelector('{self.CODEX_UPLOAD_INPUT_SELECTOR}');
                    if (!input) {{
                        input = document.createElement('input');
                        input.type = 'file';
                        input.id = '{self.CODEX_UPLOAD_INPUT_SELECTOR[1:]}';
                        input.style.display = 'none';
                        document.body.appendChild(input);
                    }}
                    input.value = '';
                    return true;
                }}
                """
            )

            api_input = locator_factory(self.CODEX_UPLOAD_INPUT_SELECTOR)
            set_input_files = getattr(api_input, "set_input_files", None)
            if not callable(set_input_files):
                return False
            set_input_files(file_path.as_posix())

            server_filename = evaluator(
                """
                async ({ nodeId }) => {
                    const input = document.querySelector('#codex-upload-input');
                    const file = input?.files?.[0];
                    const graph = globalThis.app?.graph;
                    const node =
                        graph?.getNodeById?.(nodeId) ??
                        graph?._nodes?.find((candidate) => candidate?.id === nodeId);
                    if (!file || !node || !globalThis.api?.fetchApi) {
                        return null;
                    }

                    const body = new FormData();
                    body.append('image', file);
                    const response = await globalThis.api.fetchApi('/upload/image', {
                        method: 'POST',
                        body,
                    });
                    if (!response.ok) {
                        return null;
                    }

                    const payload = await response.json();
                    const serverFilename = payload?.name;
                    if (typeof serverFilename !== 'string' || !serverFilename) {
                        return null;
                    }

                    const setWidgetValue = (name, value) => {
                        const widget = (node.widgets ?? []).find(
                            (candidate) => candidate?.name === name
                        );
                        if (widget) {
                            widget.value = value;
                        }
                    };

                    if (Array.isArray(node.widgets_values)) {
                        if (node.widgets_values.length > 0) {
                            node.widgets_values[0] = serverFilename;
                        }
                    } else if (node.widgets_values && typeof node.widgets_values === 'object') {
                        if ('video' in node.widgets_values) {
                            node.widgets_values.video = serverFilename;
                        }
                        if ('image' in node.widgets_values) {
                            node.widgets_values.image = serverFilename;
                        }
                        if (node.widgets_values.videopreview?.params) {
                            node.widgets_values.videopreview.params.filename = serverFilename;
                        }
                    }

                    setWidgetValue('video', serverFilename);
                    setWidgetValue('image', serverFilename);
                    const previewWidget = (node.widgets ?? []).find(
                        (candidate) => candidate?.name === 'videopreview'
                    );
                    if (previewWidget?.value?.params) {
                        previewWidget.value.params.filename = serverFilename;
                    }

                    node.setDirtyCanvas?.(true, true);
                    graph.setDirtyCanvas?.(true, true);
                    input.value = '';
                    return serverFilename;
                }
                """,
                {"nodeId": node_id},
            )
        except Exception:
            return False

        return isinstance(server_filename, str) and bool(server_filename.strip())

    def _extract_workflow_node_ids(self, workflow: dict[str, object]) -> list[int]:
        nodes = workflow.get("nodes")
        if not isinstance(nodes, list):
            return []

        node_ids: list[int] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            if isinstance(node_id, int):
                node_ids.append(node_id)
        return node_ids

    def _queue_graph_prompt(self, page: object, number: int) -> str | None:
        queuer = getattr(page, "queue_graph_prompt", None)
        if callable(queuer):
            task_id = queuer(number)
            if task_id is None:
                return None
            return str(task_id).strip() or None

        frame = self._find_comfyui_frame(page)
        if frame is None:
            return None

        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator):
            return None

        workflow_id = self._extract_workflow_id(self.workflow_url)
        expect_response = getattr(page, "expect_response", None)
        response_listener = getattr(page, "on", None)
        remove_listener = getattr(page, "remove_listener", None)
        if callable(response_listener) and callable(remove_listener):
            direct_task_id, response_task_id = self._queue_graph_prompt_with_response_listener(
                page,
                frame,
                number,
                workflow_id,
            )
            task_id = direct_task_id or response_task_id
        elif callable(expect_response):
            direct_task_id, response_task_id = self._queue_graph_prompt_with_response_capture(
                page,
                frame,
                number,
                workflow_id,
            )
            task_id = direct_task_id or response_task_id
        else:
            task_id = self._queue_graph_prompt_in_frame(frame, number, workflow_id)
        if task_id is None:
            return None
        return str(task_id).strip() or None

    def _queue_graph_prompt_with_response_listener(
        self,
        page: object,
        frame: object,
        number: int,
        workflow_id: str | None,
    ) -> tuple[object, str | None]:
        registrar = getattr(page, "on", None)
        remove_listener = getattr(page, "remove_listener", None)
        if not callable(registrar) or not callable(remove_listener):
            return (self._queue_graph_prompt_in_frame(frame, number, workflow_id), None)

        response_task_id: str | None = None

        def handle_response(response: object) -> None:
            nonlocal response_task_id
            if response_task_id is not None:
                return
            if "/task/create" not in str(getattr(response, "url", "")):
                return
            response_task_id = self._extract_task_id_from_response(response)

        registrar("response", handle_response)
        queue_result: object = None
        try:
            queue_result = self._queue_graph_prompt_in_frame(frame, number, workflow_id)
            if response_task_id is None:
                self._wait_for_timeout(page, self.GRAPH_QUEUE_RESPONSE_WAIT_MS)
        finally:
            remove_listener("response", handle_response)

        return (queue_result, response_task_id)

    def _queue_graph_prompt_with_response_capture(
        self,
        page: object,
        frame: object,
        number: int,
        workflow_id: str | None,
    ) -> tuple[object, str | None]:
        expect_response = getattr(page, "expect_response", None)
        if not callable(expect_response):
            return (self._queue_graph_prompt_in_frame(frame, number, workflow_id), None)

        queue_result: object = None
        try:
            with expect_response(
                lambda response: "/task/create" in str(getattr(response, "url", "")),
                timeout=self.GRAPH_QUEUE_RESPONSE_TIMEOUT_MS,
            ) as task_create_response:
                queue_result = self._queue_graph_prompt_in_frame(frame, number, workflow_id)
        except Exception:
            return (queue_result, None)

        return (
            queue_result,
            self._extract_task_id_from_response(task_create_response.value),
        )

    def _queue_graph_prompt_in_frame(
        self,
        frame: object,
        number: int,
        workflow_id: str | None,
    ) -> object:
        try:
            return self._evaluate_graph_queue_prompt(frame, number, workflow_id)
        except Exception as exc:
            if "_getWidgetByName" not in str(exc):
                return None
            if not self._inject_graph_widget_lookup_shim(frame):
                return None
            try:
                return self._evaluate_graph_queue_prompt(frame, number, workflow_id)
            except Exception:
                return None

    def _evaluate_graph_queue_prompt(
        self,
        frame: object,
        number: int,
        workflow_id: str | None,
    ) -> object:
        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator):
            return None

        return evaluator(
            """
            async ({ number, workflowId }) => {
                const app = globalThis.app;
                if (!app || typeof app.queuePrompt !== "function") {
                    return null;
                }

                const captured = [];
                const interesting = [
                    '/task/create',
                    '/task/list',
                    '/api/output/v2/history',
                ];
                const originalFetch = globalThis.fetch?.bind(globalThis);
                const originalApiFetch = globalThis.api?.fetchApi?.bind(globalThis.api);
                const captureResponse = async (url, response) => {
                    if (!interesting.some((token) => String(url).includes(token))) {
                        return response;
                    }
                    let text = '';
                    try {
                        text = await response.clone().text();
                    } catch (error) {
                        text = '';
                    }
                    captured.push({ url: String(url), text });
                    return response;
                };

                if (originalFetch) {
                    globalThis.fetch = async (...args) =>
                        captureResponse(args[0], await originalFetch(...args));
                }
                if (originalApiFetch) {
                    globalThis.api.fetchApi = async (url, options) =>
                        captureResponse(url, await originalApiFetch(url, options));
                }

                try {
                    const result = await app.queuePrompt(number);
                    await new Promise((resolve) => setTimeout(resolve, 1500));
                    const directTaskId =
                        result?.prompt_id ?? result?.taskId ?? result?.task_id ?? null;
                    if (directTaskId) {
                        return directTaskId;
                    }

                    for (const entry of captured) {
                        if (!entry?.text) {
                            continue;
                        }
                        let payload = null;
                        try {
                            payload = JSON.parse(entry.text);
                        } catch (error) {
                            payload = null;
                        }
                        if (!payload || typeof payload !== 'object') {
                            continue;
                        }

                        const createdTaskId = payload?.data?.taskId;
                        if (typeof createdTaskId === 'string' && createdTaskId) {
                            return createdTaskId;
                        }

                        const firstRecordTaskId = payload?.data?.records?.[0]?.taskId;
                        if (typeof firstRecordTaskId === 'string' && firstRecordTaskId) {
                            return firstRecordTaskId;
                        }

                        const historyTaskId = payload?.data?.[0]?.taskId;
                        if (typeof historyTaskId === 'string' && historyTaskId) {
                            return historyTaskId;
                        }
                    }

                    if (globalThis.api?.fetchApi) {
                        const listResponse = await globalThis.api.fetchApi('/task/list', {
                            method: 'POST',
                            headers: { 'content-type': 'application/json' },
                            body: JSON.stringify({
                                size: 6,
                                current: 1,
                                taskStatus: ['RUNNING', 'QUEUED'],
                                taskType: ['WORKFLOW', 'WEBAPP'],
                            }),
                        });
                        if (listResponse.ok) {
                            const listPayload = await listResponse.json();
                            const records = Array.isArray(listPayload?.data?.records)
                                ? listPayload.data.records
                                : [];
                            const matchingRecord =
                                records.find((record) =>
                                    workflowId
                                        ? String(record?.workflowId ?? '') === String(workflowId)
                                        : true
                                ) ?? records[0];
                            const listedTaskId = matchingRecord?.taskId;
                            if (typeof listedTaskId === 'string' && listedTaskId) {
                                return listedTaskId;
                            }
                        }
                    }
                    return null;
                } finally {
                    if (originalFetch) {
                        globalThis.fetch = originalFetch;
                    }
                    if (originalApiFetch) {
                        globalThis.api.fetchApi = originalApiFetch;
                    }
                }
            }
            """,
            {"number": number, "workflowId": workflow_id},
        )

    def _extract_task_id_from_response(self, response: object) -> str | None:
        payload = None

        json_reader = getattr(response, "json", None)
        if callable(json_reader):
            try:
                payload = json_reader()
            except Exception:
                payload = None

        if payload is None:
            text_reader = getattr(response, "text", None)
            if callable(text_reader):
                try:
                    payload = json.loads(text_reader())
                except Exception:
                    payload = None

        return self._extract_task_id_from_payload(payload)

    def _extract_task_id_from_payload(self, payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None

        direct_task_id = payload.get("taskId") or payload.get("task_id") or payload.get("prompt_id")
        if isinstance(direct_task_id, str) and direct_task_id.strip():
            return direct_task_id.strip()

        data = payload.get("data")
        if isinstance(data, dict):
            nested_task_id = data.get("taskId") or data.get("task_id") or data.get("prompt_id")
            if isinstance(nested_task_id, str) and nested_task_id.strip():
                return nested_task_id.strip()

            records = data.get("records")
            if isinstance(records, list):
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    record_task_id = record.get("taskId") or record.get("task_id")
                    if isinstance(record_task_id, str) and record_task_id.strip():
                        return record_task_id.strip()

        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                item_task_id = item.get("taskId") or item.get("task_id")
                if isinstance(item_task_id, str) and item_task_id.strip():
                    return item_task_id.strip()

        return None

    def _inject_graph_widget_lookup_shim(self, frame: object) -> bool:
        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator):
            return False

        try:
            injected = evaluator(
                """
                () => {
                    const graph = globalThis.app?.graph;
                    const nodes = graph?._nodes ?? graph?.nodes ?? [];
                    for (const node of nodes) {
                        if (!node || typeof node._getWidgetByName === "function") {
                            continue;
                        }
                        node._getWidgetByName = function(name) {
                            return (this.widgets ?? []).find(
                                (widget) => widget?.name === name
                            ) ?? null;
                        };
                    }
                    return nodes.length;
                }
                """
            )
        except Exception:
            return False
        return isinstance(injected, int) and injected >= 0

    def _page_has_graph_loader(self, page: object) -> bool:
        checker = getattr(page, "is_graph_loader_ready", None)
        if callable(checker):
            return bool(checker())
        loader = getattr(page, "load_graph_data", None)
        if callable(loader):
            return True
        frame = self._find_comfyui_frame(page)
        if frame is None:
            return False

        evaluator = getattr(frame, "evaluate", None)
        if not callable(evaluator):
            return False
        try:
            return bool(
                evaluator(
                    """
                    () => Boolean(
                        globalThis.app &&
                        typeof globalThis.app.loadGraphData === "function"
                    )
                    """
                )
            )
        except Exception:
            return False

    def _wait_for_timeout(self, page: object, timeout_ms: int) -> None:
        waiter = getattr(page, "wait_for_timeout", None)
        if callable(waiter):
            waiter(timeout_ms)

    def _find_comfyui_frame(self, page: object) -> object | None:
        frames = getattr(page, "frames", None)
        if callable(frames):
            frames = frames()
        if not frames:
            return None
        for frame in frames:
            if self.COMFYUI_FRAME_URL_TOKEN in str(getattr(frame, "url", "")):
                return frame
        return None

    def _extract_workflow_id(self, workflow_url: str) -> str | None:
        match = re.search(r"/workflow/(\d+)", workflow_url)
        if match is None:
            return None
        return match.group(1)

    def _find_required_locator(self, page: object, selector: str) -> object | None:
        locator_factory = getattr(page, "locator", None)
        if not callable(locator_factory):
            return None
        locator = locator_factory(selector)
        if self._locator_count(locator) <= 0:
            return None
        return self._select_locator_instance(locator)

    def _find_first_available_locator(
        self,
        page: object,
        selectors: tuple[str, ...],
        *,
        require_visible: bool,
    ) -> object | None:
        for selector in selectors:
            locator = self._find_required_locator(page, selector)
            if locator is None:
                continue
            if self._locator_is_visible(locator):
                return locator
            if not require_visible:
                return locator
        return None

    def _extract_task_id(self, page: object) -> str | None:
        for selector in self.TASK_ID_SELECTORS:
            locator = self._find_required_locator(page, selector)
            if locator is None:
                continue
            for reader_name in ("inner_text", "text_content"):
                reader = getattr(locator, reader_name, None)
                if callable(reader):
                    value = str(reader()).strip()
                    if value:
                        return value
            attribute_reader = getattr(locator, "get_attribute", None)
            if callable(attribute_reader):
                value = attribute_reader("data-task-id")
                if value:
                    return str(value).strip()
        task_id = getattr(page, "task_id", None)
        if task_id is None:
            return None
        return str(task_id).strip() or None

    def _read_task_status_text(self, page: object, task_id: str) -> str:
        del task_id
        for selector in self.TASK_STATUS_SELECTORS:
            locator = self._find_required_locator(page, selector)
            if locator is None:
                continue
            value = self._read_locator_text(locator)
            if value:
                return value
        return str(getattr(page, "task_status", "")).strip()

    def _read_locator_text(self, locator: object) -> str:
        for reader_name in ("inner_text", "text_content"):
            reader = getattr(locator, reader_name, None)
            if callable(reader):
                value = str(reader()).strip()
                if value:
                    return value
        attribute_reader = getattr(locator, "get_attribute", None)
        if callable(attribute_reader):
            for attribute_name in ("data-task-id", "data-task-status"):
                value = attribute_reader(attribute_name)
                if value:
                    return str(value).strip()
        return ""

    def _locator_count(self, locator: object) -> int:
        counter = getattr(locator, "count", None)
        if not callable(counter):
            return 0
        return int(counter())

    def _locator_is_visible(self, locator: object) -> bool:
        count = self._locator_count(locator)
        if count <= 0:
            return False
        visible = getattr(locator, "is_visible", None)
        if callable(visible):
            return bool(visible())
        return True

    def _is_login_required(self, page: object) -> bool:
        if getattr(page, "login_required", False):
            return True
        getter = getattr(page, "get_by_role", None)
        if not callable(getter):
            return False
        for button_text in self.LOGIN_BUTTON_TEXTS:
            locator = getter("button", name=button_text)
            if locator is not None and self._locator_is_visible(locator):
                return True
        return False

    def _select_locator_instance(self, locator: object) -> object:
        count = self._locator_count(locator)
        if count <= 1:
            return locator
        first = getattr(locator, "first", None)
        if first is not None:
            return first
        return locator
