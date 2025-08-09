# Explore the InvokeAI APIs

## Useful information

- InvokeAI docs: `context\refcode\InvokeAI\docs`
- InvokeAI source code: `context\refcode\InvokeAI`
- InvokeAI API list: `context\hints\invokeai-kb\invokeai-api-list.md`

## Rules

- DO NOT create scripts in workspace root
- DO NOT modify this file
- If API exploration is successful, create a demo in `<workspace>\examples\api-demo-<what-api>.py`.

## Task 1: The basic info APIs

- find out how to get the board names

## Task 2: Get the latest image from a given board

- find the latest image from board `probe`, the latest means the most recent image that was generated and saved in the board.
- download the image and save it to `./tmp/downloads/`

## Task 3: Submit a job to the queue, to do text-to-image generation with sdxl

- first, find out what API can be used to submit a job to the queue
- submit a job to the queue, doing text-to-image generation with sdxl. in order to submit such a job, you need a workflow that has a text-to-image functionality, the workflow is in `data\workflows\sdxl-text-to-image.json`
- there is an example query of using that workflow, see `data\api-calls\call-wf-sdxl-text-to-image.json`, this is want is sent to the API to submit the job.
- after submitting the job, you need to monitor the job status, and when the job is completed, print out the job details, including the generated image name.
- when the job is completed, download the image and save it to `./tmp/downloads/`

## Task 4: Job exception handling

- find out how to cancel a running job and try it
- find out what kinds of exceptions can happen when a job is submitted, and how to handle them
- implement this: when a job is failed to submit, or submitted but failed during run, print out the error message and the job details, and then cancel or ignore the job.