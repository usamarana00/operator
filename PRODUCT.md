# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: freelance software developers juggling multiple concurrent client/personal projects, who want one natural-language interface to track deadlines/milestones and monitor GitHub repo activity instead of switching between a PM tool and GitHub. Currently used by the author (single/small user base); secondary audience is bootcamp reviewers evaluating the capstone.

## Product Purpose

A multi-agent AI assistant that answers natural-language questions about a freelancer's active projects — deadlines, milestones, GitHub repo status — and automates two adjacent chores: a one-click morning briefing summarizing all projects, and a client-proposal generator that drafts and exports a PDF grounded in the user's real project context. Success: ask "what deadlines do I have this week" or "what's the status of repo X" and get a synthesized, accurate answer without opening a PM tool or GitHub; generate a usable first-draft proposal in under a minute.

## Positioning

A LangGraph-orchestrated pipeline (Planner classifies intent → routes to PM Agent and/or GitHub Agent → Response Agent synthesizes) grounded in the user's own data via RAG (Postgres + pgvector over uploaded project docs) and live GitHub REST data — not static docs — streamed step-by-step to the browser over SSE so the user watches the agent reasoning happen rather than waiting on a spinner.

## Operating Context

- Auth: GitHub OAuth (NextAuth) → backend verifies a short-lived signed JWT minted server-side.
- First run: 4-step setup wizard (OpenAI key optional, server has a fallback → select GitHub repos → name projects/add milestones → build, which fetches READMEs/commits and indexes pgvector).
- Ongoing use: chat (SSE-streamed multi-agent reasoning), sidebar with Projects/Repos/Proposals tabs, morning briefing, proposal generator + PDF export, per-project file upload to S3.
- Deployment target: Vercel (frontend) + Render (backend) + Neon (Postgres/pgvector) + AWS S3, all free tiers.

## Capabilities and Constraints

- Verified working end-to-end this session with a real GitHub account and real repos: sign-in/sign-out, setup wizard, chat (both deadline-intent and repo-intent queries), morning briefing, proposal generation + PDF download, repos tab.
- Multi-tenant by design (per-user encrypted GitHub token, isolated project/milestone data), but only ever exercised by 1-2 real accounts so far.
- Terminology: "project" = a tracked freelance engagement, optionally linked to one GitHub repo; "milestone" = a dated deliverable under a project.
- Undecided: no accessibility standard set.

## Brand Commitments

Working product name: **Keystone** (chosen this session; not yet applied across code/README/UI — currently mixed between "Freelance Agent" and "Freelance Project Assistant"). Robot emoji (🤖) used as an informal mascot/favicon stand-in; no real logo, wordmark, or color identity exists yet.

## Evidence on Hand

No testimonials, customers, or pricing exist, and none should be invented. Real evidence available: the author's own GitHub account and repos (Interview_copilot, Job_hunt, WebDev-241608361-241605246) were used to verify every flow live — this is the demonstrable dataset for any capstone walkthrough, not synthetic data.

## Product Principles

1. Ground every answer in the user's real data (RAG + live GitHub calls) — never fabricate project status.
2. Show the reasoning, don't hide it: SSE streaming of each agent step is core product value, not an implementation detail.
3. One conversational entry point should replace switching between a PM tool and GitHub, not add another dashboard to check.
4. Capstone-first: prioritize a clean, reliable happy-path demo over hardening for strangers or scale.

## Accessibility & Inclusion

None established; no product-specific requirement confirmed.
