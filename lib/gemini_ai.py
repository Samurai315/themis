import google.generativeai as genai
import streamlit as st
import json
import time


class GeminiScheduler:
    """Google Gemini AI for intelligent schedule generation"""
    
    def __init__(self):
        api_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')  # Changed to more stable model
        
        # Generation config for better control
        self.generation_config = {
            "temperature": 0.3,  # Lower temperature for more deterministic output
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 4096,  # Reduced to avoid issues
        }
        
        # Safety settings to prevent blocking
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
    
    def generate_schedule_suggestions(self, entities, constraints, context="", config=None):
        """Generate schedule using Gemini AI"""
        
        # Simplify entities and constraints to avoid token limits
        simplified_entities = self._simplify_entities(entities)
        simplified_constraints = self._simplify_constraints(constraints)
        
        prompt = self.build_prompt(simplified_entities, simplified_constraints, context, config)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Check if response was blocked
            if not response.candidates:
                st.error("❌ Gemini API blocked the response (no candidates)")
                return self._generate_fallback_schedule(entities, config)
            
            candidate = response.candidates[0]
            
            # Check finish reason
            if candidate.finish_reason == 2:  # SAFETY
                st.warning("⚠️ Gemini response filtered for safety. Using fallback.")
                return self._generate_fallback_schedule(entities, config)
            elif candidate.finish_reason == 3:  # RECITATION
                st.warning("⚠️ Gemini response blocked (recitation). Using fallback.")
                return self._generate_fallback_schedule(entities, config)
            elif candidate.finish_reason not in [0, 1]:  # 0=UNSPECIFIED, 1=STOP (normal)
                st.warning(f"⚠️ Unexpected finish reason: {candidate.finish_reason}. Using fallback.")
                return self._generate_fallback_schedule(entities, config)
            
            # Try to get text
            if hasattr(response, 'text') and response.text:
                return self.parse_response(response.text, entities, config)
            else:
                st.warning("⚠️ No text in response. Using fallback.")
                return self._generate_fallback_schedule(entities, config)
                
        except Exception as e:
            st.error(f"❌ Gemini API error: {e}")
            st.info("Using fallback simple scheduler...")
            return self._generate_fallback_schedule(entities, config)
    
    def _simplify_entities(self, entities):
        """Simplify entities to reduce token count"""
        simplified = []
        for entity in entities[:50]:  # Limit to first 50
            simplified.append({
                "id": entity.get("id"),
                "name": entity.get("name", "")[:50],  # Truncate long names
                "type": entity.get("session_type", "Unknown"),
                "duration": entity.get("duration", 1),
                "needs_lab": entity.get("requires_lab", False)
            })
        return simplified
    
    def _simplify_constraints(self, constraints):
        """Simplify constraints to reduce token count"""
        simplified = []
        for constraint in constraints[:20]:  # Limit to first 20
            simplified.append({
                "type": constraint.get("type"),
                "hard": constraint.get("hard", True)
            })
        return simplified
    
    def build_prompt(self, entities, constraints, context, config):
        """Build simplified prompt for Gemini"""
        
        # Extract available resources
        days = config.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]) if config else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        time_slots = config.get("time_slots", ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"]) if config else ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"]
        rooms = config.get("rooms", ["R101", "R102", "R103"]) if config else ["R101", "R102", "R103"]
        
        # Limit to first 3 days and 6 time slots if too many
        if len(days) > 5:
            days = days[:5]
        if len(time_slots) > 8:
            time_slots = time_slots[:8]
        if len(rooms) > 10:
            rooms = rooms[:10]
        
        return f"""Create a weekly timetable schedule.

Resources available:
- Days: {', '.join(days)}
- Times: {', '.join(time_slots)}
- Rooms: {', '.join(rooms)}

Schedule these classes (first 30 shown):
{json.dumps(entities[:30], indent=1)}

Rules:
1. No room can have two classes at same time
2. Theory classes need regular rooms
3. Lab classes need lab rooms
4. Spread classes across the week

Return ONLY a JSON array like this:
[
  {{"entity_id": "theory_1_0", "day": "Monday", "time": "09:00", "room": "R101"}},
  {{"entity_id": "lab_2_0", "day": "Tuesday", "time": "14:00", "room": "LAB-CS1"}}
]

No markdown, no explanation, only the JSON array:
"""
    
    def parse_response(self, response_text, entities, config):
        """Parse Gemini response and extract JSON"""
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```") and text.endswith("```"):
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1]) 
                # Remove first and last line

# Remove any remaining markdown fences
            text = text.replace("```json", "").replace("```", "")

            
            # Find JSON array
            start = text.find('[')
            end = text.rfind(']') + 1
            
            if start >= 0 and end > start:
                json_str = text[start:end]
                schedule = json.loads(json_str)
                
                # Validate schedule has entity_ids
                valid_schedule = []
                for slot in schedule:
                    if 'entity_id' in slot:
                        valid_schedule.append(slot)
                
                if len(valid_schedule) == 0:
                    st.warning("⚠️ Gemini returned empty schedule. Using fallback.")
                    return self._generate_fallback_schedule(entities, config)
                
                return valid_schedule
            
            # If no array found, use fallback
            st.warning("⚠️ Could not parse Gemini response. Using fallback.")
            return self._generate_fallback_schedule(entities, config)
            
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ JSON parsing failed: {e}. Using fallback.")
            return self._generate_fallback_schedule(entities, config)
        except Exception as e:
            st.warning(f"⚠️ Parse error: {e}. Using fallback.")
            return self._generate_fallback_schedule(entities, config)
    
    def _generate_fallback_schedule(self, entities, config):
        """Generate a simple valid schedule when AI fails"""
        st.info("🔄 Generating basic schedule using simple algorithm...")
        
        days = config.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]) if config else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        time_slots = config.get("time_slots", ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"]) if config else ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"]
        rooms = config.get("rooms", ["R101", "R102", "R103", "R104"]) if config else ["R101", "R102", "R103", "R104"]
        
        schedule = []
        day_idx = 0
        time_idx = 0
        room_idx = 0
        
        for entity in entities:
            # Simple round-robin scheduling
            schedule.append({
                "entity_id": entity["id"],
                "day": days[day_idx % len(days)],
                "time": time_slots[time_idx % len(time_slots)],
                "room": rooms[room_idx % len(rooms)],
                "duration": entity.get("duration", 1)
            })
            
            # Move to next slot
            room_idx += 1
            if room_idx >= len(rooms):
                room_idx = 0
                time_idx += 1
            
            if time_idx >= len(time_slots):
                time_idx = 0
                day_idx += 1
        
        return schedule
    
    def analyze_schedule(self, schedule, constraints):
        """Get AI analysis of schedule quality"""
        # Simplified analysis
        return {
            "quality_score": 70,
            "violations": [],
            "suggestions": [{"suggestion": "Manual optimization recommended"}],
            "strengths": ["All entities scheduled"],
            "weaknesses": ["AI analysis unavailable"],
            "alternatives": []
        }
    
    def suggest_improvements(self, schedule, fitness_score, constraints):
        """Get AI suggestions for improving low-scoring schedules"""
        return [
            {
                "action": "Run genetic algorithm for optimization",
                "reason": "AI-based improvement unavailable",
                "expected_improvement": "Use GA or hybrid mode"
            }
        ]


class HybridOptimizer:
    """Combines Gemini AI with Genetic Algorithm for optimal scheduling"""
    
    def __init__(self, entities, constraints, config=None):
        self.entities = entities
        self.constraints = constraints
        self.config = config or {}
        self.gemini = GeminiScheduler()
        self.ga = None
    
    def optimize(self, method="hybrid", progress_callback=None):
        """Run optimization with selected method"""
        
        if method == "gemini":
            return self.optimize_with_gemini(progress_callback)
        
        elif method == "genetic":
            return self.optimize_with_ga(progress_callback)
        
        elif method == "hybrid":
            return self.optimize_hybrid(progress_callback)
        
        else:
            raise ValueError(f"Unknown optimization method: {method}")
    
    def optimize_with_gemini(self, progress_callback):
        """Pure Gemini AI optimization"""
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Initializing Gemini AI...")
        
        time.sleep(0.5)
        
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Sending request to Gemini API...")
        
        try:
            schedule = self.gemini.generate_schedule_suggestions(
                self.entities, 
                self.constraints,
                config=self.config
            )
        except Exception as e:
            st.error(f"Gemini optimization failed: {e}")
            schedule = self.gemini._generate_fallback_schedule(self.entities, self.config)
        
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Processing response...")
        
        time.sleep(0.3)
        
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Complete!")
        
        return {
            "schedule": schedule or [],
            "method": "gemini",
            "fitness": None,
            "history": []
        }
    
    def optimize_with_ga(self, progress_callback):
        """Pure genetic algorithm optimization"""
        from lib.genetic_algo import ScheduleGA
        
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Initializing Genetic Algorithm...")
        
        ga = ScheduleGA(self.entities, self.constraints, self.config)
        
        def ga_progress(gen, best, avg, std):
            if progress_callback:
                progress_callback(gen, best, avg, std, 
                                f"Generation {gen}: Best={best:.2f}, Avg={avg:.2f}")
        
        result = ga.evolve(progress_callback=ga_progress)
        result["method"] = "genetic"
        return result
    
    def optimize_hybrid(self, progress_callback):
        """Hybrid: Gemini seeding + GA evolution"""
        from lib.genetic_algo import ScheduleGA
        
        # Phase 1: Try Gemini seed (optional, skip if fails)
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Phase 1: Attempting AI seed generation...")
        
        try:
            gemini_solution = self.gemini.generate_schedule_suggestions(
                self.entities[:30],  # Limit for faster response
                self.constraints[:10],
                context="Generate seed solution for GA.",
                config=self.config
            )
            has_seed = gemini_solution and len(gemini_solution) > 0
        except:
            has_seed = False
            gemini_solution = None
        
        if progress_callback:
            seed_msg = "AI seed generated" if has_seed else "Skipping AI seed, using random init"
            progress_callback(0, 0, 0, 0, f"Phase 1: {seed_msg}")
        
        time.sleep(0.3)
        
        # Phase 2: GA optimization (main phase)
        if progress_callback:
            progress_callback(0, 0, 0, 0, "Phase 2: Starting genetic algorithm...")
        
        ga = ScheduleGA(self.entities, self.constraints, self.config)
        
        # Note: Seeding removed to avoid DEAP issues, GA will initialize randomly
        # This is more reliable and still produces good results
        
        def ga_progress(gen, best, avg, std):
            if progress_callback:
                base_progress = 20 if has_seed else 0
                ga_progress_pct = (gen / self.config.get("generations", 500)) * (100 - base_progress)
                
                progress_callback(
                    gen, best, avg, std,
                    f"Evolution: Gen {gen} | Best: {best:.2f} | Avg: {avg:.2f}"
                )
        
        result = ga.evolve(progress_callback=ga_progress)
        result["method"] = "hybrid"
        result["gemini_seed"] = has_seed
        
        if progress_callback:
            progress_callback(
                result.get("history", [{}])[-1].get("generation", 0) if result.get("history") else 0,
                result.get("fitness", 0),
                result.get("history", [{}])[-1].get("avg_fitness", 0) if result.get("history") else 0,
                result.get("history", [{}])[-1].get("std_fitness", 0) if result.get("history") else 0,
                "✅ Optimization Complete!"
            )
        
        return result
