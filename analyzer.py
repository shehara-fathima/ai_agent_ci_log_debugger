import requests
import zipfile
import io
import re
import google.generativeai as genai

def run_analysis(owner, repo, token, gemini_key, post_to_pr=False):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    genai.configure(api_key=gemini_key)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")

    def get_failed_workflows(limit=10):
        workflows = []
        page = 1
        while len(workflows) < limit:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
            params = {"status": "failure", "per_page": 100, "page": page}
            r = requests.get(url, headers=headers, params=params)
            r.raise_for_status()
            runs = r.json().get("workflow_runs", [])
            if not runs:
                break
            workflows.extend(runs)
            page += 1
        return workflows[:limit]

    def download_logs(run_id):
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()
        logs = ""
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for file in z.infolist():
                if file.filename.endswith(".txt"):
                    with z.open(file) as f:
                        logs += f.read().decode(errors="replace") + "\n"
        return logs

    def clean_log_with_context(logs: str, max_chars: int = 10000, context_lines: int = 10) -> str:
        lines = logs.splitlines()
        keywords = ["error", "exception", "fail", "traceback", "fatal", "segfault", "undefined", "not found"]
        matched_indices = []

        # Find lines with error keywords
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in keywords):
                start = max(i - context_lines, 0)
                end = min(i + context_lines + 1, len(lines))
                matched_indices.extend(range(start, end))

        # Deduplicate and preserve order
        matched_indices = sorted(set(matched_indices))
        cleaned_lines = [lines[i] for i in matched_indices]

        cleaned_text = "\n".join(cleaned_lines)

        # Fallback: if still too short, include last part of the log
        if len(cleaned_text) < max_chars // 2:
            tail = "\n".join(lines[-context_lines * 10:])
            cleaned_text += "\n\n[...Tail of log...]\n\n" + tail

        # Ensure within max_chars
        return cleaned_text[-max_chars:]

    def analyze_with_gemini(logs: str) -> str:
        relevant_logs = clean_log_with_context(logs)
        prompt = f"""
You are a DevOps assistant. Analyze the CI/CD log below and respond with:

- ❌ **Main Error**
- 💡 **Suggested Fix**
- 📈 **Confidence Level** (high/medium/low)

Logs:
{relevant_logs}
"""
        try:
            res = gemini_model.generate_content(prompt)
            return res.text.strip()
        except Exception as e:
            return f"⚠️ Gemini error: {e}"

    def post_comment(pr_number, body):
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        r = requests.post(url, headers=headers, json={"body": body})
        return r.status_code == 201

    output = ""
    workflows = get_failed_workflows()
    if not workflows:
        return "✅ No failed workflows found."

    for wf in workflows:
        run_id = wf["id"]
        run_number = wf["run_number"]
        html_url = wf["html_url"]
        output += f"---\n### 🔎 Workflow #{run_number} ([View Logs]({html_url}))\n"

        try:
            logs = download_logs(run_id)
            analysis = analyze_with_gemini(logs)
            output += f"{analysis}\n"

            if post_to_pr:
                pull_requests = wf.get("pull_requests", [])
                if pull_requests:
                    pr_number = pull_requests[0]["number"]
                    comment = f"""🚨 **CI Failure Analysis (Workflow #{run_number})**\n\n🔗 [View Workflow Logs]({html_url})\n\n{analysis}"""
                    posted = post_comment(pr_number, comment)
                    if posted:
                        output += f"✅ Comment posted to PR #{pr_number}\n"

        except Exception as e:
            output += f"❌ Error: {e}\n"

    return output
