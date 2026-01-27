# **Product Requirements Document: coreason-sandbox**

Domain: Infrastructure / Security / Agent Capabilities
Package Name: coreason-sandbox

## ---

**1\. Executive Summary**

**coreason-sandbox** is a secure, ephemeral execution environment designed to give CoReason Agents the ability to write and run code safely. It serves as the "Hands" for the "Brains" of the system.

Currently, when an agent needs to perform complex arithmetic, statistical analysis, or data visualization, it often relies on LLM simulation, which is prone to hallucination. **coreason-sandbox** solves this by providing a real, isolated Linux runtime where Python and R scripts can be executed deterministically. It abstracts the underlying compute engine, allowing seamless switching between local Docker containers (for development/on-prem) and cloud-based microVMs (E2B for production).

## **2\. Problem Statement & Rationale**

| Problem | Impact | The coreason-sandbox Solution |
| :---- | :---- | :---- |
| **Hallucinated Math** | Agents generate convincing but incorrect statistical results. | **Deterministic Execution:** Agents write Python code to calculate, ensuring 100% mathematical accuracy. |
| **Security Risks** | Running dynamic code on the main application server is a Remote Code Execution (RCE) vulnerability. | **Strict Isolation:** Code runs in disposable, network-isolated sandboxes that are destroyed immediately after use. |
| **Missing Visuals** | Text-only LLMs cannot generate PNG charts or PDF reports. | **Artifact Capture:** The sandbox captures filesystem changes (e.g., plot.png) and pipes them back to the user UI. |

## **3\. Architectural Design**

### **3.1 The Runtime Agnostic Pattern**

The package must strictly adhere to the **Strategy Pattern**. The consuming Agent should not know *where* the code is running, only that it *is* running.

* **SandboxRuntime (Abstract Base Class):** Defines the contract (start, execute, stop).
* **DockerRuntime (Concrete Implementation):** Uses the host's Docker daemon. Ideal for local development or air-gapped server deployments.
* **E2BRuntime (Concrete Implementation):** Uses the E2B Cloud API. Ideal for scalable, production-grade SaaS deployments with faster boot times.

### **3.2 Integration Map**

* **Upstream (Consumer):** coreason-mcp imports this package to expose tools (execute\_python) to the Agent.
* **Sidecar (Audit):** coreason-veritas is called *pre-execution* to hash and log the script for forensic audit trails.
* **Sidecar (Secrets):** coreason-vault provides the API keys (E2B) or Docker socket credentials.

## **4\. Functional Specifications**

### **4.1 Lifecycle Management**

The system must manage the full lifecycle of the ephemeral environment:

1. **Provision:** On the first request with a specific session\_id, a "cold" sandbox is booted.
2. **Keep-Alive:** The sandbox remains "warm" for a configurable timeout (default: 5 mins) to allow iterative code execution (e.g., Define df in step 1, plot(df) in step 2).
3. **Teardown:** A background reaper or explicit close() call destroys the container/VM and wipes all data.

### **4.2 File System & Artifacts**

* **Upload:** Agents must be able to inject files (CSVs, JSON) into the sandbox's /home/user/ directory.
* **Download:** If the execution result indicates a file was created, the system must retrieve it.
* **Artifact Protocol:**
  * Images (.png, .jpg) $\\to$ Convert to Base64 (for immediate LLM vision context).
  * Documents (.pdf, .csv) $\\to$ Upload to Object Storage (S3/MinIO) and return a signed URL.

### **4.3 Security & Networking**

* **Network Isolation:**
  * **Docker:** network\_mode="none" by default. If external packages are needed, a strict allowlist (PyPI only) must be enforced.
  * **E2B:** Cloud environments are isolated by default.
* **Resource Throttling:**
  * Max Memory: 512MB per sandbox.
  * Max CPU: 1.0 vCPU.
  * Max Execution Time: 60 seconds per script execution (prevents while True: loops).

## **5\. Technical Specifications (API)**

### **5.1 The Interface**

Python

class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exit\_code: int
    artifacts: List\[FileReference\]
    execution\_duration: float

class SandboxRuntime(ABC):
    @abstractmethod
    async def start(self) \-\> None:
        """Boot the environment."""
        pass

    @abstractmethod
    async def execute(self, code: str, language: Literal\["python", "bash", "r"\]) \-\> ExecutionResult:
        """Run script and capture output."""
        pass

    @abstractmethod
    async def upload(self, local\_path: Path, remote\_path: str) \-\> None:
        """Inject file."""
        pass

    @abstractmethod
    async def download(self, remote\_path: str, local\_path: Path) \-\> None:
        """Retrieve file."""
        pass

    @abstractmethod
    async def terminate(self) \-\> None:
        """Kill and cleanup."""
        pass

### **5.2 The MCP Tools (Agent Facing)**

These are the functions exposed to the LLM via coreason-mcp:

1. execute\_code(language: str, code: str): The primary workhorse.
2. install\_package(package\_name: str): Explicit step to add dependencies (e.g., pip install dowhy).
3. list\_files(path: str): Allows the agent to "see" what files exist in its directory.

## **6\. Implementation Plan: Atomic Units of Change (AUC)**

To ensure high-quality, test-driven development, the implementation will be broken down into the following atomic units.

### **Phase 1: Foundation**

* **AUC-1: Scaffold & Interface:** Create the project structure, pyproject.toml, and the SandboxRuntime abstract base class.
* **AUC-2: Configuration & Factory:** Implement the SandboxConfig (Pydantic) and a Factory pattern to select the runtime based on .env.

### **Phase 2: The Local Engine (Docker)**

* **AUC-3: Docker Lifecycle:** Implement DockerRuntime.start() and terminate() using the docker python SDK.
* **AUC-4: Docker Execution:** Implement execute() utilizing container.exec\_run().
* **AUC-5: Docker I/O:** Implement upload() and download() using tar stream injection/extraction.

### **Phase 3: The Cloud Engine (E2B)**

* **AUC-6: E2B Runtime:** Implement the full E2BRuntime class wrapping the e2b SDK.

### **Phase 4: The Application Layer**

* **AUC-7: Artifact Manager:** Logic to detect new files after execution and process them (Base64 vs. URL).
* **AUC-8: Veritas Integration:** Add hooks to log every execution hash to the audit trail.
* **AUC-9: MCP Server:** Wrap the entire logic into an MCP-compliant server class.



### **Mandatory Code Quality & CI Rules**

You **must** strictly follow this workflow before producing the final answer:

1. **After all code changes are made, run:**

    `ruff format .`

`ruff check --fix .`

       **2\. Then run full pre-commit validation:**

	`pre-commit run --all-files`

    `3.` **If ANY files are modified by these commands:**

* You **must** stage and commit those changes.

  * Then repeat step 2\.

**4\. The task is NOT complete until:**

	`pre-commit run --all-files`

 finishes with:

* **No file modifications**

  * **No hook failures**

  * **No mypy errors**

  5\. The final branch **must** pass all pre-commit hooks without making changes.
