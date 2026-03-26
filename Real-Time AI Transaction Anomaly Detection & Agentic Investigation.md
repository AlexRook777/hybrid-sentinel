# **PROJECT BLUEPRINT:** 

# **THE HYBRID SENTINEL**

## **Real-Time AI Transaction Anomaly Detection & Agentic Investigation**

**Author:** Hrachov Oleksandr. AI Solution Architect

**Date:** Feb 23, 2026

**Target Platform:** Custom Back-Office Payment Gateway

**Domain:** Fintech / P2P Payment Routing

**Audio explanation (20 min):** [https://drive.google.com/file/d/1LSKKgiigVW5-BoF61TP7-eo8b5vw2c0P/view?usp=sharing](https://drive.google.com/file/d/1LSKKgiigVW5-BoF61TP7-eo8b5vw2c0P/view?usp=sharing)

## **PART I: PRODUCT MANAGEMENT & BUSINESS STRATEGY**

### **1\. Executive Summary**

The "Hybrid Sentinel" is an advanced AI-driven monitoring layer designed for a custom back-office payment gateway. Unlike traditional rule-based systems that trigger alerts based on static thresholds, this solution utilizes stateful stream processing and incremental machine learning to detect subtle shifts in transaction behavior. Furthermore, it integrates Agentic AI (LangGraph) to investigate anomalies autonomously, reducing "alert fatigue" and providing human operators with actionable business intelligence rather than raw logs.

**Two-stage payment stream data verification in the gateway:**

* **Neural network** for real-time stream analysis and alert generation.  
* **AI agent** for analyzing and filtering alerts and generating inquiries for human review.

Based on this solution, it is possible to develop analysis for various types of suspicious activities and malfunctions, including fraud.

### **2\. Business Context & Problem Statement**

In the high-speed world of P2P payments, the "Transaction Flow" is the lifeblood of the company. Currently, hundreds of transactions move from diverse merchants to various providers. The critical "Callback" phase—which confirms the success or failure of a transaction—can lag by up to 5 minutes.

**Current Pain Points:**

* **Invisible Failures:** Technical degradations in a specific provider's API may go unnoticed for 15–30 minutes, leading to massive revenue loss.  
* **Velocity Attacks:** Malicious actors (carding, balance probing) can exploit P2P routes in seconds. Standard dashboards often miss these patterns until the damage is done.  
* **High Operational Cost:** Human operators are overwhelmed by "False Positives" (alerts that aren't actually problems), leading to a slow response when a real "Black Swan" event occurs.  
* **Callback Complexity:** Matching a failed callback to a transaction that happened 5 minutes ago requires "Stateful Memory" which traditional monitoring tools lack.

### 

### **3\. Project Goals**

* **Latency Goal:** Detection of behavioral anomalies within \<10 seconds of the event.  
* **Efficiency Goal:** Reduce manual investigation time by 70% through AI-generated "Case Reports."  
* **Financial Goal:** Minimize "Revenue Leakage" by automatically identifying and flagging underperforming provider routes.  
* **Technical Goal:** Create a 100% Python-compatible stack that integrates with existing back-office infrastructure without requiring a massive Java/DevOps overhaul.

### 

### **4\. Strategic Value: Why the Company Needs This**

1. **Competitive Advantage:** In the P2P space, routing reliability is the primary differentiator. This system ensures "Merchant Satisfaction" by guaranteeing the highest possible success rate.  
2. **Risk Mitigation:** Financial regulators are increasingly focused on real-time fraud detection. The Sentinel provides a robust audit trail of AI-driven investigations.  
3. **Scalable Operations:** As transaction volume grows from "hundreds" to "thousands" per second, the company cannot hire more humans at the same rate. This AI scales horizontally.

## **PART II: ARCHITECTURAL SOLUTIONS & COMPARISON**

We have analyzed two distinct architectural paths for implementing the high-speed analyzer.

### **1\. Option A: The "Heavy Enterprise" Stack**

This approach relies on the "Big Data" ecosystem standard for Fortune 500 fintech companies.

* **Ingestion:** Apache Kafka (Cluster managed by Zookeeper/KRaft).  
* **Processing:** Apache Flink (Java/Scala) for stateful windows.  
* **Storage:** ElasticSearch for logs and ClickHouse for analytics.  
* **Pros:**  
  * Virtually infinite scalability (millions of TPS).  
  * Extremely mature ecosystem and support.  
  * Strict "Exactly-Once" processing guarantees.  
* **Cons:**  
  * **High DevOps Overhead:** Requires a dedicated team to manage Kafka and Flink clusters.  
  * **Language Barrier:** Flink is Java-native. While PyFlink exists, it is often more complex to debug and deploy.  
  * **Slow Iteration:** Updating ML models often requires complex "Savepoint" management in Flink.

### **2\. Option B: The "Hybrid Sentinel" (Selected Solution)**

This approach leverages modern, high-performance Python libraries to achieve enterprise-level results with significantly lower complexity.

* **Ingestion:** Redpanda or Direct Webhook to FastAPI.  
* **Processing:** **Bytewax** (Rust-engine, Python API) for 5-minute stateful windows.  
* **Detection:** **River (Online ML)** for real-time anomaly scoring.  
* **Investigation:** **LangGraph** for AI Agent investigation and Slack integration.  
* **Pros:**  
  * **Unified Language:** 100% Python. The same engineers who build the ML models can manage the pipeline.  
  * **Agentic Integration:** Naturally integrates with LLM-based agents for "Reasoning" about anomalies.  
  * **Deployment Speed:** Can be deployed as simple containers on standard cloud infrastructure (AWS ECS/K8s).  
* **Cons:**  
  * Lower absolute throughput than Flink (though perfectly capable of handling "hundreds to low thousands" of TPS).  
  * The ecosystem is younger than the Kafka/Flink world.

### **3\. Head-to-Head Comparison**

| Metric | Heavy Enterprise (Kafka/Flink) | Hybrid Sentinel (Bytewax/River) |
| :---- | :---- | :---- |
| **Developer Velocity** | Slow (Java/DevOps heavy) | **Fast (Python-Native)** |
| **Operational Cost** | High (Cluster maintenance) | **Low (Standard Containers)** |
| **ML Flexibility** | Moderate (Batch retraining) | **High (Online/Incremental Learning)** |
| **Investigation** | Manual (Human checks logs) | **Automated (AI Agent investigation)** |
| **Scalability** | Extreme (1M+ TPS) | **Targeted (1k \- 10k TPS)** |

## 

## **III. DEEP DIVE: THE SELECTED HYBRID SENTINEL**

### **1\. Implementation Logic (The "Why")**

We have selected **Option B (Hybrid)** because it aligns perfectly with the company's current growth stage and the team's expertise in AI/ML.

#### **A. Stateful Windowing with Bytewax**

To solve the 5-minute callback problem, Bytewax maintains a "Dictionary State" in memory.

1. A transaction is hashed into a key.  
2. The state stores the timestamp and initial\_data.  
3. When a callback arrives, it joins the state.  
4. If no callback arrives within 300 seconds, Bytewax emits a TIMEOUT event, which is immediately flagged as an anomaly.

#### **B. Continuous Learning with River**

Traditional ML requires "training" on old data. In P2P payments, "normal" changes every day. **River** learns incrementally. Every transaction update it receives makes its "internal map" of normal behavior more accurate. This allows the system to detect "Concept Drift"—where a provider's behavior changes slowly over time.

#### **C. The Investigation Graph (LangGraph)**

When the Anomaly Score exceeds 0.85, the stream "hands off" a message to LangGraph. The Agent does the following:

* **Step 1:** Queries the DB for the Merchant's historical failure rate.  
* **Step 2:** Checks if other merchants are failing with the *same* provider.  
* **Step 3:** Uses an LLM to summarize: *"Merchant Alpha is being targeted by a BIN attack on Provider X. I recommend immediate routing change."*

### **2\. Strategic Roadmap**

* **Phase 1:** Deploy Bytewax "Shadow Stream" to collect data and match callbacks.  
* **Phase 2:** Implement River for "Statistical Anomaly" detection and tune thresholds.  
* **Phase 3:** Integrate LangGraph for Slack alerts and autonomous investigation.  
* 

## **IV. CONCLUSION**

The Hybrid Sentinel represents a shift from "Monitoring" to "Observability and Reasoning." By selecting a Python-native, agent-driven stack, the company ensures it can move faster than its competitors, react more intelligently to attacks, and provide a superior, reliable gateway service to its merchants.