# VendorShield Page Explanation Guide

This guide explains the business purpose of each application page. It avoids implementation details so the system can be presented as a complete product.

## 00_Login.png — Authorised Access

**Purpose:** Restricts the procurement risk workspace to authorised audit personnel.

**Explain:** “The system starts with controlled access. The current project is designed for a procurement auditor, which is the primary end-user role defined for the dashboard.”

## 01_Command_Center.png — Portfolio Overview

**Purpose:** Gives an immediate view of the historical transaction portfolio, priority review queue, financial exposure, risk distribution, and trends.

**Explain:** “This page helps an auditor understand where attention is required before opening individual cases. Every card and chart responds to the selected filters.”

## 02_Transaction_Review.png — Review Queue

**Purpose:** Provides a searchable and sortable list of risk-screened transactions.

**Explain:** “The auditor can prioritise High-risk cases, search by transaction or supplier, and open a detailed case without reviewing every transaction manually.”

## 03_Transaction_Case_File.png — Investigation Workspace

**Purpose:** Combines transaction facts, price and payment indicators, risk reasons, and the auditor decision record.

**Explain:** “The risk score only prioritises the case. The reasons show what appears unusual, while the auditor reviews evidence and records the final status and note.”

## 04_Supplier_Intelligence.png — Supplier-Level Risk

**Purpose:** Compares suppliers by transaction volume, invoice exposure, average risk, High-risk concentration, and identity-risk signals.

**Explain:** “This page helps identify whether unusual activity is isolated to one transaction or concentrated around a supplier.”

## 05_New_Transaction_Assessment.png — New Case Evaluation

**Purpose:** Calculates a new risk score for a transaction that is not already in the historical portfolio.

**Explain:** “The auditor enters current transaction details, receives a new risk level and contributing indicators, and can save the case into the review queue for follow-up.”

## Recommended presentation order

Login → Command Center → Transaction Review → Case File → Supplier Intelligence → New Transaction Assessment.

Keep the explanation focused on the business problem, user actions, and audit outcome. Discuss architecture or model development only when specifically asked.
