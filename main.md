# Ping Anything

This repo contains a GitHub Actions workflow that keeps a Render service warm by pinging it on a schedule.

## Setup

1. The workflow pings `https://novel-trace.onrender.com/health` by default.
2. Optional: add a repository secret named `RENDER_PING_URL` to override the endpoint.
3. The workflow runs every 7 minutes by default. You can adjust the schedule in `.github/workflows/render-ping.yml` to 10 or 13 minutes later.
4. You can also trigger the workflow manually from the Actions tab.

new test
