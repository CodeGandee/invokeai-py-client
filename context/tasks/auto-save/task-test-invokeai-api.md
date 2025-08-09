# Task: Test InvokeAI API

## Objective
Test InvokeAI API at http://127.0.0.1:9090/ by performing the following operations:

## Tasks
- Upload an image (generated with OpenCV) as InvokeAI asset
- Generate an image using SDXL-based model with any prompt
- Download the generated image to `./tmp`
- Use image-to-image to generate another image and download it
- Create documentation about proper usage in `context/hints`

## Referenced Files
- `.magic-context\instructions\win32-env.md`
- `.magic-context\instructions\save-command.md`

## Environment Notes
- API endpoint: http://127.0.0.1:9090/
- Python environment managed by pixi
- Playwright available for browser automation if needed
- Windows environment