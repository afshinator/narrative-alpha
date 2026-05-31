                                                                                                                
 Narrative Alpha — End-to-End Flow                                                                                                                                                                                       
 Concept: A forensic narrative intelligence app. You type a news keyword (e.g. "AI regulation"), and it pulls articles  
 from ~9 diverse news outlets via Bright Data, runs each through 4 LLM calls and an embedding comparison, then shows    
 exactly how each outlet distorted reality — what they omitted, how they spun it, and which outlier claims they made    
 vs. what everyone else agrees on.                                                                                                                                                                                         
 ### Flow (7 steps, ~2-5 min per run)                                                                                  
                                                                                                                        
 ① User Input                                                                                                           
 Homepage has a text input + dropdown. User enters a keyword and selects a vertical (TECHNOLOGY, FINANCE, etc.). Hits   
 "Run Pipeline." Dashboard opens an SSE stream to the backend.                                                          
                                                                                                                        
 ② SERP Discovery (ingestion.py → discover_articles())                                                                  
 Backend calls Bright Data SERP API with a Google News search URL + &tbm=nws. Gets back 15 organic news results with    
 titles, snippets, URLs, source domains.                                                                                
                                                                                                                        
 ③ Article Fetch + Validation (ingestion.py → build_ingestion_manifest())                                               
 For each of the 15 SERP results, spins up 5 parallel threads calling Bright Data Web Unlocker to grab full article     
 HTML past paywalls/anti-bot. Runs each through trafilatura to extract clean body text. Then 4 validation gates:        
 - Min 300 chars, 50 words                                                                                              
 - Paywall/auth-gate keyword detection                                                                                  
 - Nav-bloat/boilerplate detection                                                                                      
 - Deduplication by domain (1 article per outlet)                                                                       
                                                                                                                        
 If < 5 articles survive → INSUFFICIENT_CORPUS_FLOOR, pipeline stops. Otherwise caps at 20.                             
                                                                                                                        
 ④ Outlet Reputation Check (pipeline.py → step 3)                                                                       
 For each source domain, checks a SQLite outlet reputation DB. If UNRATED, runs a historical backtest (2-4 LLM calls    
 scraping past articles) to establish baseline metrics like scatter_shot_anomaly_factor.                                
                                                                                                                        
 ⑤ LLM Processing (4 calls)                                                                                             
                                                                                                                        
 ┌────────────────────┬──────────────────┬────────────────────────────────────────────────────────────────────────────┐ 
 │ Call               │ Model            │ What It Does                                                               │ 
 ├────────────────────┼──────────────────┼────────────────────────────────────────────────────────────────────────────┤ 
 │ Entity             │ DeepSeek V4      │ Reads all articles, maps variant names → canonical ("Apple" → "Apple       │ 
 │ Normalization      │ Flash            │ Inc.", "Tim Cook" → "Tim Cook"). Output: {surface_form: canonical} dict.   │ 
 ├────────────────────┼──────────────────┼────────────────────────────────────────────────────────────────────────────┤ 
 │ Linguistic         │ DeepSeek V4      │ Strips adjectives, spin, euphemisms from each article. Output: flat        │ 
 │ Neutralization     │ Flash            │ declarative sentences. ("Brutal crackdown" → "Police arrested              │ 
 │                    │                  │ protesters.")                                                              │ 
 ├────────────────────┼──────────────────┼────────────────────────────────────────────────────────────────────────────┤ 
 │ Graph Extraction   │ DeepSeek V4      │ For each neutralized article, extracts a knowledge graph: nodes =          │ 
 │                    │ Flash (parallel) │ entities/events, edges = relationships. Output: {nodes: [...], edges:      │ 
 │                    │                  │ [{source, target, relationship_verb}]}.                                    │ 
 ├────────────────────┼──────────────────┼────────────────────────────────────────────────────────────────────────────┤ 
 │ Forensic Synthesis │ DeepSeek V4 Pro  │ The big one. Gets ALL data — all graphs, omission scores, spin scores,     │ 
 │                    │ w/ thinking      │ reputation records, fracture candidates. Produces a structured JSON        │ 
 │                    │                  │ forensic report.                                                           │ 
 └────────────────────┴──────────────────┴────────────────────────────────────────────────────────────────────────────┘ 
                                                                                                                        
 ⑥ Analysis (set math between steps 5 & 6)                                                                              
 - Consensus Baseline: A node (entity/event) is "consensus" if it appears in >60% of outlets' graphs.                   
 - Omission Index (Oᵢ): For each outlet, what fraction of consensus nodes did they miss? 0.0→1.0.                       
 - Framing Volatility (Vf): Cosine distance between each article's raw text embedding and its neutralized text          
   embedding. High distance = lots of spin.                                                                             
 - Scatter-Shot Anomaly (Sₐ): For each outlet, ratio of outlier claims they've historically produced that never got     
   validated by consensus.                                                                                              
                                                                                                                        
 ⑦ Report Persistence + Dashboard Display                                                                               
 Report saved as JSON to ~/.narrative_alpha/data/reports/{CLUSTER_ID}.json. Dashboard fetches via REST. Displayed in 3  
 zones:                                                                                                                 
                                                                                                                        
 ┌──────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┐ 
 │ Zone             │ What It Shows                                                                                   │ 
 ├──────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤ 
 │ Zone 1 —         │ Green-shield icon. A prose summary of what all outlets agree on, plus anchor nodes (verified    │ 
 │ Consensus Truth  │ entities) and primary verifications.                                                            │ 
 │ Baseline         │                                                                                                 │ 
 ├──────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤ 
 │ Zone 2 — Media   │ Table: one row per outlet. Columns: Omission Index (badge), Framing Volatility (badge),         │ 
 │ Distortion       │ examples of linguistic camouflage (raw → clinical). Also shows Narrative Regime Shifts (e.g.    │ 
 │ Matrix           │ outlets collectively switched from "AI regulation" → "AI safety framework").                    │ 
 ├──────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┤ 
 │ Zone 3 —         │ Reputation Warnings (high scatter-shot outlets flagged red). Outlier Signals (single-source     │ 
 │ Forensic         │ claims not yet absorbed by consensus, with convergence countdown). Reality Divergence Zones     │ 
 │ Anomalies        │ (topics where outlets disagree, with consensus stability scores). Reality Fractures             │ 
 │                  │ (head-to-head contradictory claims with supporting outlets listed).                             │ 
 └──────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┘ 
                                                                                                                        
 ### Stack                                                                                                              
                                                                                                                        
 - Scraping: Bright Data SERP API + Web Unlocker                                                                        
 - LLMs: DeepSeek V4 (Flash for cheap calls, Pro+thinking for synthesis)                                                
 - Embeddings: OpenAI text-embedding-3-small (for Vf computation)                                                       
 - Backend: FastAPI (Python), single sync pipeline thread                                                               
 - Storage: SQLite (outlet reputation DB) + JSON files (reports)                                                        
 - Frontend: React + Vite, vanilla CSS with pulse animation on PENDING status                                           
                                                                                                                        
 ### Key Design Philosophy                                                                                              
                                                                                                                        
 │ "This is not a fact-checker. It maps narrative topology — what the institutional press agrees on, who omitted what,  
 │ and who spun it."                                                                                                    
                                                                                                                        
 Every metric is scored and labeled (LOW/MED/HIGH). The LLM is never asked "what's true" — only "what did each source   
 say and how did they say it." The math (set overlap, embedding distance) is what produces the distortion metrics, not  
 the LLM.