# AGENTS.TEMPLATE.md

This document describes the agent architecture and available agents in the system.

**This file is a reference template — it is inert as `AGENTS.TEMPLATE.md`.** To
put it to work, copy it to `AGENTS.md` (`cp AGENTS.TEMPLATE.md AGENTS.md`) and
restart `pw code`, which reads `AGENTS.md` at session start.

---

## ⚠️ Security Policy & Access Restrictions

**STRICT INSTRUCTION FOR ALL AGENTS:**
Under no circumstances may any agent read, access, log, parse, or transmit sensitive files, credentials, secret environment files (`.env`, `.env.*`), or log files (`*.log`, `.logs`). These files are strictly off-limits.

---

## Available Agents

### 1. Root Agent (`root_agent`)
- **Description**: A Central Orchestration Assistant that interprets user requests and delegates them to specialized agents to fulfill the user's request.
- **Primary Role**: Intercepts incoming user requests, provides direct answers when possible, and delegates specialized requests to appropriate agents.

### 2. Document Generation Agent (`docgen_agent`)
- **Description**: An agent which specializes in generating documents in various formats based on user-provided content. It can create PDF and DOCX.
- **Trigger Conditions**: Explicit commands to generate a document in PDF or DOCX format, or requests to download a generated document file.
- **Restrictions**: Does not handle slides (`.pptx`) or requests without explicit document file generation commands.

### 3. File & Coding Agent (`file_and_coding_agent`)
- **Description**: Handles the content of files explicitly uploaded by the user and any query requiring general code execution (e.g., plot generation, data exploration, analysis, calculations).
- **Trigger Conditions**:
  1. Files have been explicitly uploaded (`.pdf`, `.png`, `.csv`, `.txt`, `.pptx`, `.docx`, etc.).
  2. Queries where code execution is required to answer or parse file-like/structured data.
  3. General code execution tasks (calculations, data visualization, script execution).
