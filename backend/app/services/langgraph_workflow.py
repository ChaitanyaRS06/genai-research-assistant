# backend/app/services/langgraph_workflow.py
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import json
import logging
import openai
from dataclasses import dataclass

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings

logger = logging.getLogger(__name__)

# Define the state structure for LangGraph
class AgenticRAGState(TypedDict):
    """State object that gets passed between nodes in the LangGraph workflow"""
    # Core query information
    question: str
    user_id: int
    is_admin: bool
    
    # Workflow control
    iteration: int
    max_iterations: int
    current_stage: str
    needs_more_info: bool
    
    # Search results
    local_results: List[Dict]
    web_results: List[Dict]
    
    # Processing chain
    messages: Annotated[List, add_messages]
    intermediate_answers: List[str]
    reasoning_steps: List[Dict]
    
    # Final outputs
    final_answer: str
    confidence_score: float
    sources: List[Dict]

class LangGraphAgenticWorkflow:
    """
    LangGraph-based implementation of agentic RAG workflow
    
    This provides a more structured approach to autonomous decision-making
    with explicit state transitions and conditional routing.
    """
    
    def __init__(self, search_service, web_search_service):
        self.search_service = search_service
        self.web_search_service = web_search_service
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges"""
        
        # Create the state graph
        workflow = StateGraph(AgenticRAGState)
        
        # Add nodes for each stage of the workflow
        workflow.add_node("analyze_question", self._analyze_question_node)
        workflow.add_node("local_search", self._local_search_node)
        workflow.add_node("evaluate_local", self._evaluate_local_node)
        workflow.add_node("web_search", self._web_search_node)
        workflow.add_node("evaluate_combined", self._evaluate_combined_node)
        workflow.add_node("generate_intermediate", self._generate_intermediate_node)
        workflow.add_node("synthesize_final", self._synthesize_final_node)
        
        # Set the entry point
        workflow.set_entry_point("analyze_question")
        
        # Add conditional edges with decision logic
        workflow.add_edge("analyze_question", "local_search")
        workflow.add_edge("local_search", "evaluate_local")
        
        # Conditional routing based on local search results
        workflow.add_conditional_edges(
            "evaluate_local",
            self._should_do_web_search,
            {
                "web_search": "web_search",
                "generate": "generate_intermediate",
                "end": "synthesize_final"
            }
        )
        
        workflow.add_edge("web_search", "evaluate_combined")
        
        # Conditional routing for iteration control
        workflow.add_conditional_edges(
            "evaluate_combined",
            self._should_iterate,
            {
                "iterate": "generate_intermediate",
                "synthesize": "synthesize_final"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_intermediate",
            self._check_completeness,
            {
                "continue": "web_search",
                "complete": "synthesize_final"
            }
        )
        
        workflow.add_edge("synthesize_final", END)
        
        return workflow.compile()
    
    async def execute_langgraph_workflow(self, question: str, user, db) -> Dict[str, Any]:
        """Execute the LangGraph-based agentic workflow"""
        
        workflow_start = datetime.utcnow()
        
        # Initialize state
        initial_state = {
            "question": question,
            "user_id": user.id,
            "is_admin": user.is_admin,
            "iteration": 0,
            "max_iterations": 3,
            "current_stage": "start",
            "needs_more_info": True,
            "local_results": [],
            "web_results": [],
            "messages": [HumanMessage(content=question)],
            "intermediate_answers": [],
            "reasoning_steps": [],
            "final_answer": "",
            "confidence_score": 0.0,
            "sources": []
        }
        
        # Add user and db to state for access in nodes
        initial_state["_user"] = user
        initial_state["_db"] = db
        
        try:
            # Execute the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            workflow_time = (datetime.utcnow() - workflow_start).total_seconds() * 1000
            
            return {
                "answer": final_state["final_answer"],
                "sources": final_state["sources"],
                "workflow_metadata": {
                    "iterations_performed": final_state["iteration"],
                    "workflow_type": "langgraph_agentic",
                    "stages_completed": len([s for s in final_state["reasoning_steps"] if s.get("stage")]),
                    "workflow_time_ms": workflow_time,
                    "final_confidence": final_state["confidence_score"]
                },
                "reasoning_steps": final_state["reasoning_steps"],
                "retrieval_method": "langgraph_agentic",
                "confidence": final_state["confidence_score"],
                "langgraph_features": {
                    "state_based_execution": True,
                    "conditional_routing": True,
                    "structured_decision_making": True,
                    "message_passing": len(final_state["messages"]),
                    "autonomous_iteration_control": True
                }
            }
            
        except Exception as e:
            logger.error(f"LangGraph workflow failed: {e}")
            return {
                "answer": f"LangGraph workflow encountered an error: {str(e)}",
                "sources": [],
                "workflow_metadata": {"error": str(e)},
                "reasoning_steps": [{"error": str(e), "timestamp": datetime.utcnow().isoformat()}],
                "retrieval_method": "error",
                "confidence": 0.0
            }
    
    # Node implementations
    
    async def _analyze_question_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Analyze question and create execution plan"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Use OpenAI to analyze question complexity and intent
        analysis_prompt = f"""Analyze this question for agentic processing: "{state['question']}"

        Determine:
        1. Complexity level (1-5, where 5 is most complex)
        2. Required information types (factual, analytical, current, comparative)
        3. Likely data sources needed (internal_docs, web_search, both)
        4. Estimated processing stages needed

        Respond with JSON:
        {{
            "complexity": 1-5,
            "types": ["factual", "analytical", "current", "comparative"],
            "sources": ["internal_docs", "web_search", "both"],
            "stages": 1-3
        }}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse analysis (simplified)
            analysis_text = response.choices[0].message.content.strip()
            # Extract JSON (basic parsing)
            if "{" in analysis_text:
                json_start = analysis_text.find("{")
                json_end = analysis_text.rfind("}") + 1
                analysis = json.loads(analysis_text[json_start:json_end])
            else:
                analysis = {"complexity": 3, "types": ["analytical"], "sources": ["both"], "stages": 2}
            
        except Exception as e:
            logger.warning(f"Question analysis failed: {e}")
            analysis = {"complexity": 3, "types": ["analytical"], "sources": ["both"], "stages": 2}
        
        # Update state
        state["current_stage"] = "analysis_complete"
        state["max_iterations"] = analysis.get("stages", 2)
        
        # Add to reasoning chain
        state["reasoning_steps"].append({
            "node": "analyze_question",
            "stage": "planning",
            "action": "Analyzed question complexity and requirements",
            "analysis": analysis,
            "timestamp": timestamp
        })
        
        # Add to message chain
        state["messages"].append(SystemMessage(
            content=f"Question analyzed. Complexity: {analysis.get('complexity', 'unknown')}, "
                   f"Sources needed: {', '.join(analysis.get('sources', []))}"
        ))
        
        return state
    
    async def _local_search_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Perform local document search"""
        
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Perform local search
            local_results = await self.search_service.search_documents(
                query=state["question"],
                user=state["_user"],
                db=state["_db"],
                limit=5
            )
            
            # Convert to serializable format
            state["local_results"] = [
                {
                    "chunk_id": chunk.id,
                    "content": chunk.chunk_text,
                    "similarity": float(similarity),
                    "document_name": chunk.document.filename if hasattr(chunk, 'document') else 'Unknown',
                    "page_number": chunk.page_number
                }
                for chunk, similarity in local_results
            ]
            
            # Update stage
            state["current_stage"] = "local_search_complete"
            
            # Add to reasoning chain
            state["reasoning_steps"].append({
                "node": "local_search",
                "stage": "retrieval",
                "action": f"Completed local search, found {len(state['local_results'])} relevant chunks",
                "results_count": len(state["local_results"]),
                "avg_similarity": sum(r["similarity"] for r in state["local_results"]) / len(state["local_results"]) if state["local_results"] else 0,
                "timestamp": timestamp
            })
            
            # Add to message chain
            state["messages"].append(AIMessage(
                content=f"Local search completed. Found {len(state['local_results'])} relevant document chunks."
            ))
            
        except Exception as e:
            logger.error(f"Local search node failed: {e}")
            state["reasoning_steps"].append({
                "node": "local_search",
                "stage": "retrieval",
                "action": "Local search failed",
                "error": str(e),
                "timestamp": timestamp
            })
        
        return state
    
    async def _evaluate_local_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Evaluate local search results sufficiency"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Calculate local search quality metrics
        local_count = len(state["local_results"])
        avg_similarity = sum(r["similarity"] for r in state["local_results"]) / local_count if local_count > 0 else 0
        
        # Determine if local results are sufficient
        is_sufficient = (
            local_count >= 3 and 
            avg_similarity > 0.7
        )
        
        # Update state
        state["current_stage"] = "local_evaluation_complete"
        
        # Add to reasoning chain
        state["reasoning_steps"].append({
            "node": "evaluate_local",
            "stage": "evaluation",
            "action": "Evaluated local search results",
            "local_sufficient": is_sufficient,
            "metrics": {
                "result_count": local_count,
                "avg_similarity": avg_similarity,
                "sufficiency_threshold": 0.7
            },
            "timestamp": timestamp
        })
        
        return state
    
    async def _web_search_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Perform web search"""
        
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Perform web search
            web_results = await self.web_search_service.search(
                query=state["question"],
                max_results=3
            )
            
            # Convert to serializable format
            state["web_results"] = [
                {
                    "title": result.title,
                    "content": result.content,
                    "url": result.url,
                    "score": result.score
                }
                for result in web_results
            ]
            
            # Update stage
            state["current_stage"] = "web_search_complete"
            
            # Add to reasoning chain
            state["reasoning_steps"].append({
                "node": "web_search", 
                "stage": "retrieval",
                "action": f"Completed web search, found {len(state['web_results'])} results",
                "results_count": len(state["web_results"]),
                "timestamp": timestamp
            })
            
            # Add to message chain
            state["messages"].append(AIMessage(
                content=f"Web search completed. Found {len(state['web_results'])} relevant web results."
            ))
            
        except Exception as e:
            logger.error(f"Web search node failed: {e}")
            state["reasoning_steps"].append({
                "node": "web_search",
                "stage": "retrieval", 
                "action": "Web search failed",
                "error": str(e),
                "timestamp": timestamp
            })
        
        return state
    
    async def _evaluate_combined_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Evaluate combined search results"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Calculate combined quality metrics
        total_sources = len(state["local_results"]) + len(state["web_results"])
        has_both_types = len(state["local_results"]) > 0 and len(state["web_results"]) > 0
        
        # Update iteration counter
        state["iteration"] += 1
        
        # Update stage
        state["current_stage"] = "combined_evaluation_complete"
        
        # Add to reasoning chain
        state["reasoning_steps"].append({
            "node": "evaluate_combined",
            "stage": "evaluation",
            "action": "Evaluated combined search results",
            "iteration": state["iteration"],
            "metrics": {
                "total_sources": total_sources,
                "has_hybrid_sources": has_both_types,
                "local_count": len(state["local_results"]),
                "web_count": len(state["web_results"])
            },
            "timestamp": timestamp
        })
        
        return state
    
    async def _generate_intermediate_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Generate intermediate answer and assess completeness"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Build context from current results
        context_parts = []
        
        if state["local_results"]:
            context_parts.append("=== LOCAL DOCUMENTS ===")
            for result in state["local_results"][:3]:
                context_parts.append(f"Document: {result['document_name']}")
                context_parts.append(f"Content: {result['content'][:300]}...")
                context_parts.append("---")
        
        if state["web_results"]:
            context_parts.append("=== WEB RESULTS ===")
            for result in state["web_results"][:2]:
                context_parts.append(f"Title: {result['title']}")
                context_parts.append(f"Content: {result['content'][:300]}...")
                context_parts.append("---")
        
        context = "\n".join(context_parts)
        
        # Generate intermediate answer
        prompt = f"""Based on available information, provide an intermediate answer to: "{state['question']}"

        Context:
        {context}
        
        Format your response as:
        ANSWER: [intermediate answer]
        COMPLETENESS: [score 1-10]
        MISSING: [what's still needed]
        CONFIDENCE: [score 1-10]"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse response (simplified)
            answer = self._extract_after_marker(response_text, "ANSWER:")
            completeness_str = self._extract_after_marker(response_text, "COMPLETENESS:")
            confidence_str = self._extract_after_marker(response_text, "CONFIDENCE:")
            
            completeness = self._extract_number(completeness_str, default=5)
            confidence = self._extract_number(confidence_str, default=5) / 10.0
            
            # Update state
            state["intermediate_answers"].append(answer)
            state["needs_more_info"] = completeness < 7 and state["iteration"] < state["max_iterations"]
            state["current_stage"] = "intermediate_generated"
            
            # Add to reasoning chain
            state["reasoning_steps"].append({
                "node": "generate_intermediate",
                "stage": "generation",
                "action": "Generated intermediate answer",
                "completeness": completeness,
                "confidence": confidence,
                "needs_more_info": state["needs_more_info"],
                "iteration": state["iteration"],
                "timestamp": timestamp
            })
            
            # Add to message chain
            state["messages"].append(AIMessage(content=f"Intermediate answer generated. Completeness: {completeness}/10"))
            
        except Exception as e:
            logger.error(f"Intermediate generation failed: {e}")
            state["reasoning_steps"].append({
                "node": "generate_intermediate",
                "stage": "generation",
                "action": "Intermediate generation failed",
                "error": str(e),
                "timestamp": timestamp
            })
        
        return state
    
    async def _synthesize_final_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Node: Generate final synthesized answer"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Build complete context
        all_context = []
        
        if state["local_results"]:
            all_context.append("=== INTERNAL DOCUMENTS ===")
            for result in state["local_results"]:
                all_context.append(f"Document: {result['document_name']}, Page: {result.get('page_number', 'N/A')}")
                all_context.append(f"Content: {result['content']}")
                all_context.append("---")
        
        if state["web_results"]:
            all_context.append("=== WEB SOURCES ===")
            for result in state["web_results"]:
                all_context.append(f"Title: {result['title']}")
                all_context.append(f"URL: {result['url']}")
                all_context.append(f"Content: {result['content']}")
                all_context.append("---")
        
        context = "\n".join(all_context)
        
        # Generate final answer
        synthesis_prompt = f"""Provide a comprehensive final answer using all available information from the multi-stage analysis.

        Original Question: {state['question']}
        
        All Available Information:
        {context}
        
        Previous Analysis Stages: {len(state['intermediate_answers'])} intermediate answers generated
        
        Instructions:
        1. Synthesize all information into a comprehensive answer
        2. Cite sources clearly (internal documents vs web sources)
        3. Demonstrate how the multi-stage LangGraph workflow provided better coverage
        4. Address any gaps or limitations found
        
        Final Answer:"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=800,
                temperature=0.3
            )
            
            final_answer = response.choices[0].message.content.strip()
            
            # Calculate final confidence
            final_confidence = self._calculate_final_confidence(state)
            
            # Compile sources
            sources = self._compile_sources(state)
            
            # Update state
            state["final_answer"] = final_answer
            state["confidence_score"] = final_confidence
            state["sources"] = sources
            state["current_stage"] = "workflow_complete"
            
            # Add to reasoning chain
            state["reasoning_steps"].append({
                "node": "synthesize_final",
                "stage": "synthesis",
                "action": "Generated final synthesized answer",
                "final_confidence": final_confidence,
                "total_sources": len(sources),
                "workflow_complete": True,
                "timestamp": timestamp
            })
            
            # Add to message chain
            state["messages"].append(AIMessage(content="Final answer synthesized from multi-stage LangGraph workflow"))
            
        except Exception as e:
            logger.error(f"Final synthesis failed: {e}")
            state["final_answer"] = f"Synthesis failed: {str(e)}"
            state["confidence_score"] = 0.2
        
        return state
    
    # Conditional edge functions
    
    def _should_do_web_search(self, state: AgenticRAGState) -> str:
        """Decide whether to perform web search based on local results"""
        
        local_count = len(state["local_results"])
        
        if local_count == 0:
            return "web_search"  # No local results, need web search
        elif local_count < 3:
            return "web_search"  # Insufficient local results
        else:
            avg_similarity = sum(r["similarity"] for r in state["local_results"]) / local_count
            if avg_similarity < 0.7:
                return "web_search"  # Low quality local results
            else:
                return "generate"  # Good local results, generate answer
    
    def _should_iterate(self, state: AgenticRAGState) -> str:
        """Decide whether to continue iterating or synthesize final answer"""
        
        if state["iteration"] >= state["max_iterations"]:
            return "synthesize"  # Hit max iterations
        
        # Check if we have enough information
        total_sources = len(state["local_results"]) + len(state["web_results"])
        if total_sources >= 5:
            return "synthesize"  # Have enough sources
        
        return "iterate"  # Continue iterating
    
    def _check_completeness(self, state: AgenticRAGState) -> str:
        """Check if intermediate answer is complete enough"""
        
        if state["needs_more_info"] and state["iteration"] < state["max_iterations"]:
            return "continue"  # Need more information
        else:
            return "complete"  # Answer is complete
    
    # Helper methods
    
    def _extract_after_marker(self, text: str, marker: str) -> str:
        """Extract content after a marker"""
        if marker in text:
            start = text.find(marker) + len(marker)
            end = text.find("\n", start)
            if end == -1:
                end = len(text)
            return text[start:end].strip()
        return ""
    
    def _extract_number(self, text: str, default: int = 5) -> int:
        """Extract first number from text"""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else default
    
    def _calculate_final_confidence(self, state: AgenticRAGState) -> float:
        """Calculate final confidence score"""
        
        base_confidence = 0.6
        
        # Boost from multiple sources
        total_sources = len(state["local_results"]) + len(state["web_results"])
        source_boost = min(total_sources * 0.05, 0.2)
        
        # Boost from hybrid sources
        hybrid_boost = 0.1 if (len(state["local_results"]) > 0 and len(state["web_results"]) > 0) else 0
        
        # Boost from multiple iterations (thorough analysis)
        iteration_boost = min(state["iteration"] * 0.05, 0.15)
        
        return min(base_confidence + source_boost + hybrid_boost + iteration_boost, 1.0)
    
    def _compile_sources(self, state: AgenticRAGState) -> List[Dict]:
        """Compile all sources from local and web results"""
        
        sources = []
        
        # Add local sources
        for result in state["local_results"]:
            sources.append({
                "type": "document",
                "document_name": result["document_name"],
                "page_number": result.get("page_number"),
                "similarity_score": result.get("similarity"),
                "text_preview": result["content"][:200] + "..."
            })
        
        # Add web sources
        for result in state["web_results"]:
            sources.append({
                "type": "web",
                "title": result["title"],
                "url": result["url"],
                "score": result.get("score"),
                "text_preview": result["content"][:200] + "..."
            })
        
        return sources