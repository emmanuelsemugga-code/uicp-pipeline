

BLOCK 1 — WHAT UICP IS (PLAINEST ENGLISH)

```
UICP is a safety gate for computer decisions.

Your computer makes a decision. Before the decision is acted on,
UICP checks it against your list of rules. If all rules are obeyed,
UICP says ALLOW. If any rule is broken, UICP says BLOCK.

UICP does not make the decision. You do. UICP only checks the rules.

Think of UICP as a security guard at a door. You give the guard a list:
  - "Only people with a badge can enter."
  - "No one can enter after midnight."
The guard stops everyone, checks the list, and either lets them in
or turns them away. The guard never makes up new rules.

UICP does exactly that — but for computer systems, 24 hours a day,
without mistakes.
```

---

BLOCK 2 — WHAT YOU NEED BEFORE STARTING

```
You need four things. All are free.

1. A computer with internet access.
   - A normal laptop or desktop is fine.
   - A cloud server is also fine.

2. Docker installed on that computer.
   - Docker is a tool that runs UICP in a sealed box so you don't
     need to install anything else.
   - If you do not have Docker, open your web browser and go to:
       https://docs.docker.com/get-docker/
   - Follow the instructions for your computer (Windows, Mac, or Linux).
   - This takes about 10 minutes. It is a one-time step.

3. A program called a "terminal" or "command prompt".
   - On Windows: press the Windows key, type "cmd", press Enter.
   - On Mac: press Command+Space, type "terminal", press Enter.
   - On Linux: you already have one.

4. A text editor to write a small file.
   - On Windows: Notepad is already installed.
   - On Mac: TextEdit is already installed.
   - You do not need anything special.

That is all. You do NOT need Python, databases, or any programming
knowledge for the basic setup.
```

---

BLOCK 3 — GET THE UICP SOFTWARE

```
Open your terminal. Type the following command and press Enter:

    docker pull emmanuelsemugga-code/uicp-gateway:latest

This downloads UICP from the internet. It may take 2-5 minutes.
You will see progress bars. Wait until it finishes.

If the above command does not work (maybe the image is not yet public),
use this command instead. It builds UICP from the source code on your
computer. You must be inside the UICP project folder for this to work:

    docker build -t uicp-gateway .

Either way, after the command finishes, UICP is on your computer.
```

---

BLOCK 4 — WRITE YOUR RULES (CONSTRAINT FILE)

```
Create a new file on your computer named exactly:

    constraints.json

Open the file in your text editor. Copy and paste the exact text below.
This creates two rules: (1) age must be 18 or more, (2) risk must be
25 or less.

{
  "objective_id": "MY_RULES",
  "canonical_constraints": [
    {
      "identity_string": "AGE_CHECK",
      "canonical_form": "age >= 18",
      "classification": "LINEAR_SINGLE_VAR",
      "derived_from": [],
      "reason": ""
    },
    {
      "identity_string": "RISK_CHECK",
      "canonical_form": "risk <= 25",
      "classification": "LINEAR_SINGLE_VAR",
      "derived_from": [],
      "reason": ""
    }
  ],
  "equivalence_groups": [],
  "dominance_removed": [],
  "execution_result": {}
}

Save the file. Remember where you saved it. You will need the folder
path in the next step.
```

---

BLOCK 5 — CHOOSE YOUR API KEY

```
UICP needs a password to protect it. This password is called an
"API key". You make up the password yourself.

Choose a long, random string. Example:

    sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55

Write it down. You will need it every time you talk to UICP.
Never share it with anyone you do not trust.
```

---

BLOCK 6 — START UICP

```
Open your terminal. You will type ONE command to start UICP.

The command has several parts. I will explain each part so you
understand, but you only need to copy and paste the final command.

PARTS EXPLAINED IN PLAIN ENGLISH:
  - docker run : start a new container
  - -d : run in the background (you can close the terminal)
  - --name uicp-gateway : give it a name so you can refer to it later
  - -p 5000:5000 : make UICP reachable on your computer's port 5000
  - -e API_KEY="..." : set your password inside the container
  - -e CONSTRAINT_SET_PATH="/etc/constraint_set.json" : tell UICP
    where to find your rules file inside the container
  - -v /path/to/your/constraints.json:/etc/constraint_set.json :
    connect your local rules file to the container
  - uicp-gateway : the name of the UICP software

NOW COPY AND PASTE THE COMMAND BELOW.
BEFORE YOU PASTE, change two things:
  1. Replace the API key with the one you chose.
  2. Replace /path/to/your/constraints.json with the real path to your
     file. If your file is in the current folder, use $(pwd)/constraints.json
     on Mac/Linux, or %cd%\constraints.json on Windows.

--- FOR LINUX / MAC ---

docker run -d \
  --name uicp-gateway \
  -p 5000:5000 \
  -e API_KEY="sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55" \
  -e CONSTRAINT_SET_PATH="/etc/constraint_set.json" \
  -v $(pwd)/constraints.json:/etc/constraint_set.json \
  uicp-gateway

--- FOR WINDOWS ---

docker run -d ^
  --name uicp-gateway ^
  -p 5000:5000 ^
  -e API_KEY="sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55" ^
  -e CONSTRAINT_SET_PATH="/etc/constraint_set.json" ^
  -v %cd%\constraints.json:/etc/constraint_set.json ^
  uicp-gateway

Press Enter. The command runs. You will see a long string of letters
and numbers. That means UICP started successfully.
```

---

BLOCK 7 — CHECK THAT UICP IS ALIVE

```
In the terminal, type this command and press Enter:

    curl http://localhost:5000/health

You should see exactly this response:

    {"status":"healthy"}

If you see that, UICP is working. You have succeeded.

If you see "Connection refused", wait 10 seconds and try again.
If it still fails, check the Troubleshooting block at the end.
```

---

BLOCK 8 — HOW TO SEND A DECISION TO UICP (TWO WAYS)

```
There are two ways to send a decision to UICP.

WAY 1: SEND RAW TEXT (UICP EXTRACTS THE NUMBERS)

Use this if your system produces normal sentences like
"Client age is 35, risk score is 8."

The body of your request looks like this:

{
  "model_output": "Client age is 35, risk score is 8.",
  "binding_schema": {
    "age":  {"method": "regex", "pattern": "(?:age|client age)[=: ]*(?P<value>\\d+)"},
    "risk": {"method": "regex", "pattern": "(?:risk score|risk)[=: ]*(?P<value>\\d+)"}
  },
  "constraint_set": {
    "canonical_constraints": [
      {"identity_string": "AGE_CHECK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"},
      {"identity_string": "RISK_CHECK", "canonical_form": "risk <= 25", "classification": "LINEAR_SINGLE_VAR"}
    ]
  },
  "output_id": "req-001"
}

WAY 2: SEND ALREADY-EXTRACTED NUMBERS

Use this if your system already produces clean numbers like
{"age": 35, "risk": 8}.

{
  "bindings": {"age": 35, "risk": 8},
  "constraint_set": {
    "canonical_constraints": [
      {"identity_string": "AGE_CHECK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"},
      {"identity_string": "RISK_CHECK", "canonical_form": "risk <= 25", "classification": "LINEAR_SINGLE_VAR"}
    ]
  },
  "output_id": "req-001"
}

For both ways, you must include two headers in your HTTP request:
  Content-Type: application/json
  X-API-Key: your-api-key-here

The next block shows how to do this with curl.
```

---

BLOCK 9 — UNDERSTANDING UICP'S ANSWER

```
UICP always answers with a JSON object. The most important field
is "status". It can be one of three values:

1. "ALLOW"  → All rules were obeyed. The decision is safe to proceed.
2. "BLOCK"  → At least one rule was broken. The decision should NOT
              proceed. The "violations" list tells you which rules
              were broken and what the numbers were.
3. "GATEWAY_UNAVAILABLE" → UICP itself has a problem. It cannot check
              the rules right now. You should treat this exactly like
              a BLOCK. Do NOT proceed until a human investigates.

Example of a BLOCK response:

{
  "status": "BLOCK",
  "violations": [
    {
      "constraint_identity": "AGE_CHECK",
      "canonical_form": "age >= 18",
      "actual_value_hash": "sha256...",
      "expected": "age >= 18"
    }
  ],
  "decision_id": "abc123...",
  "output_id": "req-001",
  "timestamp": "2026-06-10T12:00:00Z"
}

The "violations" list tells you exactly which rule failed.
The "canonical_form" tells you what the rule was.
```

---

BLOCK 10 — TEST UICP WITH CURL (COPY‑PASTE EXERCISE)

```
Open your terminal. Copy and paste the first command to test an
ALLOW decision. Then copy and paste the second command to test a
BLOCK decision.

--- TEST 1: SHOULD BE ALLOWED (age=35, risk=8) ---

curl -X POST http://localhost:5000/enforce \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55" \
  -d '{
    "bindings": {"age": 35, "risk": 8},
    "constraint_set": {
      "canonical_constraints": [
        {"identity_string": "AGE_CHECK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"},
        {"identity_string": "RISK_CHECK", "canonical_form": "risk <= 25", "classification": "LINEAR_SINGLE_VAR"}
      ]
    },
    "output_id": "test-001"
  }'

--- TEST 2: SHOULD BE BLOCKED (age=16, risk=8) ---

curl -X POST http://localhost:5000/enforce \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55" \
  -d '{
    "bindings": {"age": 16, "risk": 8},
    "constraint_set": {
      "canonical_constraints": [
        {"identity_string": "AGE_CHECK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"},
        {"identity_string": "RISK_CHECK", "canonical_form": "risk <= 25", "classification": "LINEAR_SINGLE_VAR"}
      ]
    },
    "output_id": "test-002"
  }'
```

---

BLOCK 11 — HOW TO CHANGE YOUR RULES

```
When you need to update your rules:

1. Open your constraints.json file in your text editor.
2. Change the rules. Add new ones, remove old ones, edit numbers.
3. Save the file.
4. In the terminal, type:

       docker restart uicp-gateway

5. Wait 10 seconds. The new rules are now active.
6. Test with a curl command to make sure the new rules work.

There is no step 7. That is all.
```

---

BLOCK 12 — WHAT TO DO WHEN SOMETHING GOES WRONG

```
PROBLEM 1: "Connection refused" when checking health
  → The container is not running.
  → Type: docker start uicp-gateway
  → If that fails, re-run the docker run command from Block 6.

PROBLEM 2: "401 Unauthorized" or "Missing API Key"
  → You forgot the X-API-Key header, or the key is wrong.
  → Check that your request includes the exact key you chose.

PROBLEM 3: "500 Internal Server Error"
  → Your constraints.json file is missing, or the JSON is broken.
  → Open constraints.json and check for missing commas or quotes.
  → You can paste your JSON at https://jsonlint.com to check it.

PROBLEM 4: Every decision is BLOCKED
  → Your bindings do not satisfy the rules.
  → Check your numbers against your rules manually.

PROBLEM 5: Every decision is ALLOWED, even wrong ones
  → The gateway may be using old rules.
  → Restart the gateway: docker restart uicp-gateway
  → Check that your constraints.json file has the correct rules.
```

---

BLOCK 13 — MAKING UICP SAFE FOR REAL CUSTOMERS

```
When you move from testing to real use:

1. Use a stronger API key. At least 64 random characters.
2. Never send requests over plain HTTP on the internet. Put UICP
   behind an HTTPS proxy (like nginx or your cloud load balancer).
3. Run at least two copies of UICP for reliability. If one fails,
   the other keeps working.
4. Store your constraints.json file in version control (Git).
5. Export and archive UICP's audit logs regularly.
6. Set up monitoring that calls /health every minute and alerts
   you if UICP is down.
```

---

BLOCK 14 — PROGRAMMING EXAMPLES (FOR ENGINEERS)

```
PYTHON:

import requests
API_KEY = "sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55"
URL = "http://localhost:5000/enforce"

def check(bindings):
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    body = {
        "bindings": bindings,
        "constraint_set": {
            "canonical_constraints": [
                {"identity_string": "AGE_CHECK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"},
                {"identity_string": "RISK_CHECK", "canonical_form": "risk <= 25", "classification": "LINEAR_SINGLE_VAR"}
            ]
        },
        "output_id": "py-req-001"
    }
    return requests.post(URL, json=body, headers=headers).json()

JAVASCRIPT (Node.js):

const API_KEY = "sk-mYSuperSecr3tKeyTh4tN0bodyCanGue55";
const URL = "http://localhost:5000/enforce";

async function check(bindings) {
    const res = await fetch(URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({
            bindings,
            constraint_set: {
                canonical_constraints: [
                    { identity_string: "AGE_CHECK", canonical_form: "age >= 18", classification: "LINEAR_SINGLE_VAR" },
                    { identity_string: "RISK_CHECK", canonical_form: "risk <= 25", classification: "LINEAR_SINGLE_VAR" }
                ]
            },
            output_id: "js-req-001"
        })
    });
    return await res.json();
}

JAVA:

// Use java.net.http.HttpClient (Java 11+)
// Full code provided in the complete specification document.
// Contact support if you need the exact Java class.
```

---

END OF REFERENCE ORCHESTRATOR.

This document is designed so that anyone, anywhere in the world, with any level of technical skill, can deploy and use UICP. No assumptions. No missing steps. If something is unclear, the answer is in one of the blocks above.
