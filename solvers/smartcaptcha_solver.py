from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass
from typing import Iterable, Sequence

import requests
from playwright.sync_api import Frame, Locator, Page, TimeoutError as PlaywrightTimeout


class SmartCaptchaError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptchaResult:
    coordinates: Sequence[tuple[float, float]]


API_IN_URL = "https://rucaptcha.com/in.php"
API_RES_URL = "https://rucaptcha.com/res.php"


def _collect_candidate_frames(page: Page) -> list[Frame]:
    frames: list[Frame] = []
    for frame in page.frames:
        url = (frame.url or "").lower()
        if "captcha" in url or "smartcaptcha" in url:
            frames.append(frame)
    return frames


def _snapshot_captcha_image(frame: Frame) -> tuple[bytes, Locator]:
    image = frame.locator("img").first
    image.wait_for(state="visible", timeout=10_000)
    png_bytes = image.screenshot(type="png")
    return png_bytes, image


def _request_solution(api_key: str, image_bytes: bytes, max_poll_time: float = 120.0) -> CaptchaResult:
    files = {"file": ("captcha.png", image_bytes, "image/png")}
    data = {
        "key": api_key,
        "method": "post",
        "coordinatescaptcha": 1,
        "json": 1,
    }
    response = requests.post(API_IN_URL, data=data, files=files, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != 1:
        raise SmartCaptchaError(f"RuCaptcha error: {payload}")
    captcha_id = payload["request"]

    started = time.time()
    while time.time() - started < max_poll_time:
        poll = requests.get(
            API_RES_URL,
            params={"key": api_key, "action": "get", "id": captcha_id, "json": 1},
            timeout=15,
        )
        poll.raise_for_status()
        result = poll.json()
        if result.get("status") == 1:
            coords_payload = result.get("request", {})
            coords = coords_payload.get("coordinates") if isinstance(coords_payload, dict) else None
            if not coords:
                raise SmartCaptchaError(f"RuCaptcha empty coordinates: {coords_payload}")
            parsed = [(float(point["x"]), float(point["y"])) for point in coords]
            return CaptchaResult(coordinates=parsed)
        time.sleep(3)
    raise SmartCaptchaError("RuCaptcha timeout waiting for coordinates")


def _click_coordinates(image: Locator, coordinates: Iterable[tuple[float, float]]) -> None:
    box = image.bounding_box()
    if not box:
        raise SmartCaptchaError("captcha image bounding box unavailable")
    origin_x = box["x"]
    origin_y = box["y"]
    for x, y in coordinates:
        image.page.mouse.click(origin_x + x, origin_y + y)
        time.sleep(0.3)


def _submit_button(frame: Frame) -> None:
    try:
        button = frame.locator("button").first
        button.click(timeout=2_000)
    except PlaywrightTimeout:
        pass


def solve_smartcaptcha(page: Page, api_key: str) -> bool:
    if not api_key:
        return False
    frames = _collect_candidate_frames(page)
    if not frames:
        return False
    frame = frames[0]
    png_bytes, image = _snapshot_captcha_image(frame)
    solution = _request_solution(api_key, png_bytes)
    _click_coordinates(image, solution.coordinates)
    _submit_button(frame)
    time.sleep(2.0)
    return True


__all__ = ["solve_smartcaptcha", "SmartCaptchaError", "CaptchaResult"]