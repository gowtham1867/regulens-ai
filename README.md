# ReguLens AI 🛡️
### Evidence-Driven Regulatory Intelligence Engine for AICTE Institutional Scrutiny

[![Deployment](https://img.shields.io/badge/Vercel-Live%20Deployment-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://regulens-ai.vercel.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React%2019-Vite%208-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%2F%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

**ReguLens AI** is an end-to-end regulatory compliance and document scrutiny platform designed for the All India Council for Technical Education (AICTE). It automates and streamlines institutional affiliation reviews, document validation, land and safety norm enforcement, contradiction detection, and official communication between Scrutiny Officers and participating institutions.

---

## 👥 Contributors

This project was designed, developed, and contributed by:

1. **Kaviya M**
2. **Ilakiya**
3. **Gayathri**
4. **Agaram Bharath**
5. **Agilesh R**
6. **Gowtham Balaji P**

---

## 🌐 Live Deployment

- **Production App**: [https://regulens-ai.vercel.app](https://regulens-ai.vercel.app)
- **Deployment Build**: [https://regulens-1k5jtytoc-gowtham1867.vercel.app](https://regulens-1k5jtytoc-gowtham1867.vercel.app)
- **GitHub Repository**: [https://github.com/gowtham1867/regulens-ai](https://github.com/gowtham1867/regulens-ai)

---

## ✨ Key Capabilities

- **Separate Role Gateways**:
  - **Institution Portal** (`/login`): Clean Mailchimp-style landing experience for college registrars and administrators.
  - **AICTE Scrutiny Officer Gateway** (`/officer/login`): Restricted access portal for authorized nodal scrutiny officers.
  - **New Institution Account Registration** (`/institution/register`): Direct registration workflow with server-side validation and AICTE officer approval.
- **TrustGraph Evidence Triplet Cross-Verification**:
  - Relational knowledge graph modeling institutions, programs, land parcels, building plans, and statutory certificates.
  - Automated graph cycle and contradiction detection.
- **Intelligent Document OCR & Metadata Scrutiny**:
  - Extraction and validation of statutory documents (Fire NOC, Land Deeds, University Affiliations, Building Safety Certificates).
  - Anomaly detection flagging expired certificates, mismatched survey numbers, and intake overages.
- **Database-Backed Scrutiny & Approval Workflow**:
  - Official decision actions: **Approve**, **Reject**, **Request Clarification**, **Request Documents**, and **Mark Under Review**.
  - Mandatory structured rejection justification dialog requiring compliance rule citations and supporting evidence references.
- **Institution Notification System**:
  - Real-time notification routing keeping institutions updated on scrutinized applications with strict multi-tenant isolation.
- **Tamper-Evident SHA-256 Audit Trail**:
  - Immutable event logs tracking every review, upload, status change, and officer decision.

---

## 🔑 Default Test Credentials

| Role | Portal Link | Username / Email | Password |
| :--- | :--- | :--- | :--- |
| **Approved Institution (Apex)** | [/login](https://regulens-ai.vercel.app/login) | `apex@institution.edu.in` | `Institute@123` |
| **AICTE Scrutiny Officer** | [/officer/login](https://regulens-ai.vercel.app/officer/login) | `officer@aicte-india.org` | `Officer@123` |
| **New Institution Enrollment** | [/institution/register](https://regulens-ai.vercel.app/institution/register) | *(Create an account)* | *(Min. 8 characters)* |

---

## 🏗️ Project Architecture

```text
regulens-ai/
├── api/
│   ├── index.py                 # Vercel Serverless Function entrypoint
│   └── requirements.txt         # Serverless Python dependencies
├── backend/
│   ├── app/
│   │   ├── api/v1/              # FastAPI REST endpoints
│   │   ├── core/                # JWT auth, security, hashing
│   │   ├── models/              # SQLAlchemy database models
│   │   ├── schemas/             # Pydantic validation schemas
│   │   └── services/            # OCR, TrustGraph, Rules engine, Notifications
│   ├── regulens.db              # Pre-seeded SQLite database
│   └── requirements.txt         # Backend Python requirements
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI & modal components
│   │   ├── context/             # React AuthContext
│   │   ├── pages/               # Institution & Officer pages
│   │   └── services/            # Axios / Fetch API client
│   ├── package.json             # React dependencies
│   └── vite.config.ts           # Vite + TailwindCSS config
├── vercel.json                  # Vercel monorepo build & routing rules
├── package.json                 # Monorepo build orchestrator
└── README.md                    # Project documentation & contributors
```

---

## 🚀 Running Locally

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
# Navigate to backend and install requirements
pip install -r backend/requirements.txt

# Start the FastAPI server on port 8000
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at `http://127.0.0.1:8000/api/docs`.

### 3. Frontend Setup
```bash
# In a separate terminal, navigate to frontend and install dependencies
cd frontend
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` to access the application.

---

## 📄 License & Attribution

Developed for the **AICTE Regulatory Scrutiny & Compliance Automation System**.  
© 2026 ReguLens AI.
