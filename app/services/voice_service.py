# app/services/voice_service.py - IMPROVED VERSION WITH FIXED ACCURACY
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import date
import logging

logger = logging.getLogger(__name__)

# Use the ServiceType from models to maintain consistency
from app.models.service import ServiceType

class VoiceProcessingService:
    """Improved service for processing voice transcripts with enhanced accuracy"""
    
    # Enhanced automotive parts dictionary with comprehensive keywords and patterns
    PARTS_DICT = {
        # Engine & Fluids
        'engine oil': {
            'name': 'Engine Oil', 
            'keywords': ['engine oil', 'motor oil', 'oil change', 'changed oil', 'oil replaced', 'oil', 'lubricant'],
            'patterns': [
                r'engine\s+oil',
                r'motor\s+oil',
                r'oil\s+change',
                r'changed\s+oil',
                r'replaced\s+oil'
            ],
            'category': 'Fluid', 
            'avg_price': 500,
            'common_with': ['oil filter']
        },
        'oil filter': {
            'name': 'Oil Filter', 
            'keywords': ['oil filter', 'filter change', 'replaced filter', 'filter', 'oil element'],
            'patterns': [
                r'oil\s+filter',
                r'filter\s+change',
                r'replaced\s+filter'
            ],
            'category': 'Filter', 
            'avg_price': 200,
            'common_with': ['engine oil', 'air filter']
        },
        'air filter': {
            'name': 'Air Filter', 
            'keywords': ['air filter', 'air cleaner', 'cabin filter', 'air filter change', 'ac filter'],
            'patterns': [
                r'air\s+filter',
                r'cabin\s+filter',
                r'ac\s+filter'
            ],
            'category': 'Filter', 
            'avg_price': 300,
            'common_with': ['engine oil', 'oil filter']
        },
        'fuel filter': {
            'name': 'Fuel Filter', 
            'keywords': ['fuel filter', 'petrol filter', 'diesel filter'],
            'patterns': [r'fuel\s+filter'],
            'category': 'Filter', 
            'avg_price': 400
        },
        'coolant': {
            'name': 'Coolant', 
            'keywords': ['coolant', 'anti freeze', 'radiator coolant', 'cooling fluid'],
            'patterns': [r'coolant', r'anti\s*freeze'],
            'category': 'Fluid', 
            'avg_price': 350
        },
        
        # Brakes
        'brake pad': {
            'name': 'Brake Pads', 
            'keywords': ['brake pad', 'brake pads', 'pads', 'front pads', 'rear pads', 'disc pads'],
            'patterns': [
                r'brake\s+pads?',
                r'front\s+pads',
                r'rear\s+pads',
                r'disc\s+pads'
            ],
            'category': 'Brakes', 
            'avg_price': 800,
            'common_with': ['brake disc', 'brake fluid']
        },
        'brake disc': {
            'name': 'Brake Disc', 
            'keywords': ['brake disc', 'brake disk', 'disc brake', 'rotor', 'brake rotors', 'discs'],
            'patterns': [
                r'brake\s+(?:disc|disk|rotor)s?',
                r'discs?\s+brake',
                r'rotors?\s+brake'
            ],
            'category': 'Brakes', 
            'avg_price': 1500
        },
        'brake fluid': {
            'name': 'Brake Fluid', 
            'keywords': ['brake fluid', 'brake oil', 'hydraulic fluid', 'dot fluid'],
            'patterns': [r'brake\s+fluid', r'brake\s+oil'],
            'category': 'Fluid', 
            'avg_price': 250,
            'common_with': ['brake pad', 'brake disc']
        },
        
        # Electrical
        'battery': {
            'name': 'Battery', 
            'keywords': ['battery', 'accumulator', 'car battery', 'new battery'],
            'patterns': [r'battery', r'accumulator'],
            'category': 'Electrical', 
            'avg_price': 2500
        },
        'spark plug': {
            'name': 'Spark Plug', 
            'keywords': ['spark plug', 'sparkplug', 'ignition plug', 'spark plugs'],
            'patterns': [r'spark\s*plugs?', r'ignition\s+plugs?'],
            'category': 'Electrical', 
            'avg_price': 150
        },
        'alternator': {
            'name': 'Alternator', 
            'keywords': ['alternator', 'generator'],
            'patterns': [r'alternator', r'generator'],
            'category': 'Electrical', 
            'avg_price': 3000
        },
        
        # Tires & Wheels
        'tire': {
            'name': 'Tire', 
            'keywords': ['tire', 'tyre', 'tires', 'tyres', 'wheel', 'wheels', 'new tyre', 'tire replaced'],
            'patterns': [
                r'tires?',
                r'tyres?',
                r'wheel\s+tire',
                r'new\s+(?:tire|tyre)'
            ],
            'category': 'Tires', 
            'avg_price': 2000,
            'common_with': ['wheel alignment', 'wheel balancing']
        },
        'wheel alignment': {
            'name': 'Wheel Alignment', 
            'keywords': ['wheel alignment', 'alignment', 'wheel align', 'alignment done'],
            'patterns': [r'wheel\s+alignment', r'alignment'],
            'category': 'Service', 
            'avg_price': 300,
            'common_with': ['tire', 'wheel balancing']
        },
        'wheel balancing': {
            'name': 'Wheel Balancing', 
            'keywords': ['wheel balancing', 'balancing', 'wheel balance', 'balance wheels'],
            'patterns': [r'wheel\s+balancing', r'balancing'],
            'category': 'Service', 
            'avg_price': 200,
            'common_with': ['tire', 'wheel alignment']
        },
        
        # AC
        'ac gas': {
            'name': 'AC Gas', 
            'keywords': ['ac gas', 'refrigerant', 'cooling gas', 'ac refrigerant'],
            'patterns': [r'ac\s+gas', r'refrigerant', r'cooling\s+gas'],
            'category': 'AC', 
            'avg_price': 800
        },
        
        # Belts
        'timing belt': {
            'name': 'Timing Belt', 
            'keywords': ['timing belt', 'cambelt', 'timing chain'],
            'patterns': [r'timing\s+(?:belt|chain)', r'cam\s+belt'],
            'category': 'Engine', 
            'avg_price': 3000
        },
        
        # Wiper
        'wiper blade': {
            'name': 'Wiper Blades', 
            'keywords': ['wiper blade', 'wiper', 'windshield wiper', 'wiper blades'],
            'patterns': [r'wiper\s+(?:blades?|blade)', r'windshield\s+wiper'],
            'category': 'Exterior', 
            'avg_price': 500
        },
    }
    
    # Service actions with more variations and improved patterns
    ACTIONS = {
        'replaced': {
            'keywords': ['replaced', 'changed', 'installed', 'fitted', 'put in', 'new', 'renewed', 'substituted'],
            'patterns': [
                r'replaced\s+(?:the\s+)?([^.]+?)(?:\.|with|and|,)',
                r'changed\s+(?:the\s+)?([^.]+?)(?:\.|with|and|,)',
                r'new\s+([^.]+?)(?:\.|and|,)',
                r'installed\s+new\s+([^.]+?)'
            ]
        },
        'repaired': {
            'keywords': ['repaired', 'fixed', 'mended', 'adjusted', 'tightened', 'corrected', 'serviced'],
            'patterns': [
                r'repaired\s+(?:the\s+)?([^.]+?)',
                r'fixed\s+(?:the\s+)?([^.]+?)',
                r'adjusted\s+(?:the\s+)?([^.]+?)'
            ]
        },
        'checked': {
            'keywords': ['checked', 'inspected', 'examined', 'tested', 'verified', 'looked at'],
            'patterns': [
                r'checked\s+(?:the\s+)?([^.]+?)',
                r'inspected\s+(?:the\s+)?([^.]+?)',
                r'tested\s+(?:the\s+)?([^.]+?)'
            ]
        },
        'cleaned': {
            'keywords': ['cleaned', 'washed', 'polished', 'lubricated', 'greased', 'degreased'],
            'patterns': [
                r'cleaned\s+(?:the\s+)?([^.]+?)',
                r'lubricated\s+(?:the\s+)?([^.]+?)',
                r'greased\s+(?:the\s+)?([^.]+?)'
            ]
        },
    }
    
    # Service types with more keywords (matching ServiceType enum)
    SERVICE_TYPES = {
        'regular_service': {
            'keywords': ['service', 'maintenance', 'regular', 'periodic', 'scheduled', 'routine', 'full service', 'complete service'],
            'patterns': [r'full\s+service', r'complete\s+service', r'regular\s+service']
        },
        'repair': {
            'keywords': ['repair', 'broken', 'damaged', 'faulty', 'not working', 'issue', 'problem', 'fix'],
            'patterns': [r'repair', r'broken', r'not\s+working']
        },
        'inspection': {
            'keywords': ['inspection', 'check', 'test', 'diagnosis', 'evaluation', 'scan'],
            'patterns': [r'inspection', r'check', r'diagnosis']
        },
        'emergency': {
            'keywords': ['emergency', 'urgent', 'breakdown', 'tow', 'stranded', 'immediate'],
            'patterns': [r'emergency', r'breakdown', r'urgent']
        },
        'warranty': {
            'keywords': ['warranty', 'guarantee', 'under warranty'],
            'patterns': [r'warranty', r'guarantee']
        },
    }
    
    # Special patterns for improved detection
    SPECIAL_PATTERNS = {
        'full_service': [
            r'full\s+service\s+(?:with\s+)?([^.]+)',
            r'complete\s+service\s+(?:with\s+)?([^.]+)',
            r'service\s+done\s+(?:with\s+)?([^.]+)'
        ],
        'comma_separated_list': [
            r'(?:with|including)\s+([^.]*?)(?:\.|and|$)',
            r'(?:replaced|changed)\s+([^.]*?)(?:\.|and|$)',
            r'done\s+([^.]*?)(?:\.|and|$)'
        ],
        'multi_part': [
            r'([^,]+?)\s+and\s+([^,]+?)(?:\.|,)',
            r'([^,]+?),\s+([^,]+?)\s+and\s+([^,]+?)'
        ]
    }
    
    def __init__(self):
        """Initialize with compiled regex patterns for better performance"""
        self.compiled_patterns = self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for better performance"""
        compiled = {}
        
        # Compile cost patterns
        compiled['cost'] = [
            re.compile(r'total\s*[:\-]?\s*[Rs$]?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'[Rs$]\s*(\d+(?:\.\d+)?)\s*(?:in total|total|altogether)', re.IGNORECASE),
            re.compile(r'cost\s*(?:is|of|was)?\s*[:\-]?\s*[Rs$]?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d+)?)\s*(?:rs|rupees|Rs|inr)\s*(?:in total|total)?', re.IGNORECASE),
            re.compile(r'[Rs$]\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'charged\s*[Rs$]?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'bill\s*(?:of|for)?\s*[Rs$]?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
            re.compile(r'(\d+)\s*(?:rupees|rs|rp)', re.IGNORECASE),
        ]
        
        # Compile odometer patterns
        compiled['odometer'] = [
            re.compile(r'(\d{4,6})\s*(?:km|kms|kilometer|kilometers)', re.IGNORECASE),
            re.compile(r'odometer\s*(?:reading|is|at)?\s*[:\-]?\s*(\d+)', re.IGNORECASE),
            re.compile(r'(\d+)\s*(?:on the odometer|reading|on odometer)', re.IGNORECASE),
            re.compile(r'at\s*(\d+)\s*km', re.IGNORECASE),
            re.compile(r'(\d+)\s*km\s*(?:done|completed|run)', re.IGNORECASE),
            re.compile(r'(\d+)\s*(?:km\s*reading)', re.IGNORECASE),
        ]
        
        # Compile quantity patterns
        compiled['quantity'] = [
            re.compile(r'all\s*(\d+)?\s*(?:tires|tyres|wheels)', re.IGNORECASE),
            re.compile(r'(\d+)\s*(?:tires|tyres|wheels)', re.IGNORECASE),
            re.compile(r'both\s*(?:front|rear)', re.IGNORECASE),
            re.compile(r'front\s*and\s*rear', re.IGNORECASE),
            re.compile(r'(\d+)\s*(?:pcs|pieces|units)', re.IGNORECASE),
            re.compile(r'(\d+)\s*(?:set|sets)', re.IGNORECASE),
        ]
        
        return compiled
    
    def process_transcript(self, transcript: str) -> Dict[str, any]:
        """Improved voice transcript processing with enhanced accuracy"""
        if not transcript or not transcript.strip():
            # Handle empty transcript
            return {
                'transcript': transcript,
                'service_type': ServiceType.REGULAR_SERVICE,
                'parts_replaced': [],
                'parts_repaired': [],
                'labor_cost': 0.0,
                'parts_cost': 0.0,
                'total_cost': 0.0,
                'odometer_reading': None,
                'date_info': {},
                'work_summary': 'No transcript provided',
                'confidence_score': 0.0,
                'parsed_successfully': False,
                'raw_parts_found': []
            }
            
        text_lower = transcript.lower()
        
        # Pre-process text for better parsing
        preprocessed_text = self._preprocess_text(text_lower)
        
        # Extract service type with better matching
        service_type = self._extract_service_type(preprocessed_text)
        
        # Extract parts using multiple strategies
        parts_replaced = self._extract_parts_with_improved_detection(preprocessed_text, 'replaced')
        parts_repaired = self._extract_parts_with_improved_detection(preprocessed_text, 'repaired')
        
        # Handle comma-separated lists (fix for Test 3 failure)
        comma_parts = self._extract_comma_separated_parts(preprocessed_text)
        parts_replaced.extend(comma_parts)
        
        # Apply context-aware rules (for full service, etc.)
        context_parts = self._apply_context_rules(preprocessed_text, parts_replaced)
        parts_replaced.extend(context_parts)
        
        # Also look for parts without explicit action (implied replacement)
        implied_parts = self._extract_implied_parts(preprocessed_text)
        parts_replaced.extend(implied_parts)
        
        # Remove duplicates while preserving order
        parts_replaced = self._remove_duplicate_parts(parts_replaced)
        parts_repaired = self._remove_duplicate_parts(parts_repaired)
        
        # Extract costs with better patterns
        labor_cost = self._extract_cost(preprocessed_text, ['labor', 'work', 'service', 'charge', 'fee'])
        parts_cost = self._extract_cost(preprocessed_text, ['parts', 'spares', 'components', 'material'])
        total_cost = self._extract_total_cost(preprocessed_text)
        
        # Extract odometer reading
        odometer = self._extract_odometer(preprocessed_text)
        
        # Extract date references
        date_info = self._extract_date_info(preprocessed_text)
        
        # Calculate improved confidence score
        confidence = self._calculate_improved_confidence(
            preprocessed_text, parts_replaced, parts_repaired, total_cost, odometer
        )
        
        # Generate better work summary
        work_summary = self._generate_detailed_work_summary(
            parts_replaced, parts_repaired, service_type, total_cost
        )
        
        # Calculate estimated costs if not mentioned
        if total_cost == 0 and (parts_replaced or parts_repaired):
            total_cost = self._estimate_cost(parts_replaced, parts_repaired, labor_cost)
        
        # Get raw parts found for debugging/accuracy testing
        raw_parts_found = [p['name'] for p in parts_replaced]
        
        return {
            'transcript': transcript,
            'service_type': service_type,
            'parts_replaced': parts_replaced,
            'parts_repaired': parts_repaired,
            'labor_cost': labor_cost,
            'parts_cost': parts_cost,
            'total_cost': total_cost or (labor_cost + parts_cost),
            'odometer_reading': odometer,
            'date_info': date_info,
            'work_summary': work_summary,
            'confidence_score': confidence,
            'parsed_successfully': confidence > 0.3,
            'raw_parts_found': raw_parts_found
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better parsing"""
        # Replace common abbreviations
        replacements = {
            ' & ': ' and ',
            ' + ': ' and ',
            ' w/ ': ' with ',
            ' w ': ' with ',
            ' ac ': ' air conditioning ',
            ' a/c ': ' air conditioning ',
            ' km ': ' kilometers ',
            ' kms ': ' kilometers ',
            ' rs ': ' rupees ',
            ' Rs': ' rupees ',
            'inr ': 'rupees ',
        }
        
        processed = text
        for old, new in replacements.items():
            processed = processed.replace(old, new)
        
        # Remove extra spaces
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        return processed
    
    def _extract_service_type(self, text: str) -> str:
        """Improved service type extraction with pattern matching"""
        text_lower = text.lower()
        
        for service_type, data in self.SERVICE_TYPES.items():
            # Check patterns first
            for pattern in data.get('patterns', []):
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return service_type
            
            # Then check keywords
            for keyword in data.get('keywords', []):
                if re.search(rf'\b{keyword}\b', text_lower):
                    return service_type
        
        # Default based on keywords
        if any(word in text_lower for word in ['full service', 'complete service', 'major service']):
            return ServiceType.REGULAR_SERVICE
        
        # Check for emergency/breakdown context
        if any(word in text_lower for word in ['emergency', 'breakdown', 'stranded', 'urgent']):
            return ServiceType.EMERGENCY
        
        return ServiceType.REGULAR_SERVICE
    
    def _extract_parts_with_improved_detection(self, text: str, action_type: str) -> List[Dict]:
        """Improved part extraction with multiple detection strategies"""
        parts_found = []
        
        # Strategy 1: Check each part's patterns
        for part_id, part_info in self.PARTS_DICT.items():
            # Check all patterns for this part
            for pattern in part_info.get('patterns', []):
                if re.search(pattern, text, re.IGNORECASE):
                    # Found the part, now check for action
                    action_data = self.ACTIONS.get(action_type, {})
                    
                    # Check action keywords
                    for action_keyword in action_data.get('keywords', []):
                        # Look for action near the part
                        context_pattern = rf'{action_keyword}\s+[^.]*?\b{re.escape(part_info["keywords"][0])}\b'
                        if re.search(context_pattern, text, re.IGNORECASE):
                            quantity = self._extract_quantity(text, part_info["keywords"][0])
                            parts_found.append(self._create_part_dict(
                                part_id, part_info, action_type, quantity, pattern
                            ))
                            break
        
        return parts_found
    
    def _extract_comma_separated_parts(self, text: str) -> List[Dict]:
        """Extract parts from comma-separated lists (fix for Test 3)"""
        parts_found = []
        
        # Pattern for comma-separated lists after "with" or "including"
        list_patterns = [
            r'(?:with|including)\s+(.+?)(?:\.|for|at|Rs|$)',
            r'(?:replaced|changed)\s+(.+?)(?:\.|for|at|Rs|$)',
            r'full service\s+(?:with\s+)?(.+?)(?:\.|for|at|Rs|$)',
            r'service\s+(?:with\s+)?(.+?)(?:\.|for|at|Rs|$)',
        ]
        
        for pattern in list_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                list_text = match.group(1)
                # Split by commas, "and", "&"
                items = re.split(r'[,\s]+and\s+|\s*,\s*|\s+&\s+', list_text)
                
                for item in items:
                    item = item.strip()
                    if item and len(item) > 2:  # Ignore very short items
                        # Find which part this matches
                        for part_id, part_info in self.PARTS_DICT.items():
                            for keyword in part_info['keywords']:
                                if keyword in item.lower():
                                    # Also check for the part in the full item
                                    if any(kw in item.lower() for kw in part_info['keywords']):
                                        quantity = self._extract_quantity(text, keyword)
                                        parts_found.append(self._create_part_dict(
                                            part_id, part_info, 'replaced', quantity, 'comma_list'
                                        ))
                                        break
        
        return parts_found
    
    def _apply_context_rules(self, text: str, existing_parts: List[Dict]) -> List[Dict]:
        """Apply context-aware rules to add missing parts"""
        added_parts = []
        text_lower = text.lower()
        
        # Rule 1: Full service implies certain parts
        if any(pattern in text_lower for pattern in ['full service', 'complete service', 'major service']):
            common_parts = ['engine oil', 'oil filter', 'air filter']
            for part_id in common_parts:
                if part_id in self.PARTS_DICT:
                    # Check if already found
                    if not any(p['id'] == part_id for p in existing_parts + added_parts):
                        part_info = self.PARTS_DICT[part_id]
                        added_parts.append(self._create_part_dict(
                            part_id, part_info, 'replaced', 1, 'full_service_context'
                        ))
        
        # Rule 2: "Tire" often implies balancing and alignment
        if any('tire' in p['id'] for p in existing_parts) or 'tire' in text_lower or 'tyre' in text_lower:
            related_parts = ['wheel alignment', 'wheel balancing']
            for part_id in related_parts:
                if part_id in self.PARTS_DICT:
                    # Check context
                    if re.search(r'balancing|alignment', text_lower):
                        if not any(p['id'] == part_id for p in existing_parts + added_parts):
                            part_info = self.PARTS_DICT[part_id]
                            added_parts.append(self._create_part_dict(
                                part_id, part_info, 'replaced', 1, 'tire_context'
                            ))
        
        # Rule 3: Check for common part combinations
        for part in existing_parts:
            part_id = part['id']
            if part_id in self.PARTS_DICT:
                common_with = self.PARTS_DICT[part_id].get('common_with', [])
                for related_part_id in common_with:
                    if related_part_id in self.PARTS_DICT:
                        if not any(p['id'] == related_part_id for p in existing_parts + added_parts):
                            part_info = self.PARTS_DICT[related_part_id]
                            added_parts.append(self._create_part_dict(
                                related_part_id, part_info, 'replaced', 1, 'common_combo'
                            ))
        
        return added_parts
    
    def _extract_implied_parts(self, text: str) -> List[Dict]:
        """Extract parts that are implied to be replaced"""
        parts_found = []
        text_lower = text.lower()
        
        # Common implied replacement patterns
        implied_patterns = [
            (r'oils?\s+change', 'engine oil'),  # oil change -> engine oil
            (r'oil\s+and\s+filter', 'oil filter'), # oil and filter -> oil filter
            (r'new\s+battery', 'battery'),     # new battery -> battery
            (r'filter\s+change', 'oil filter'), # filter change -> oil filter
            (r'brake\s+service', 'brake pad'),  # brake service -> brake pad
            (r'brake\s+job', 'brake pad'),      # brake job -> brake pad
            (r'full\s+service', 'multiple'),    # full service -> multiple parts
            (r'tire\s+rotation', 'tire'),       # tire rotation -> tire service
            (r'wheel\s+service', 'wheel alignment'), # wheel service -> alignment
        ]
        
        for pattern, part_hint in implied_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if part_hint == 'multiple':
                    # Full service implies multiple parts
                    common_service_parts = ['engine oil', 'oil filter', 'air filter']
                    for part_key in common_service_parts:
                        if part_key in self.PARTS_DICT:
                            part_info = self.PARTS_DICT[part_key]
                            parts_found.append(self._create_part_dict(
                                part_key, part_info, 'replaced', 1, 'implied_full_service'
                            ))
                elif part_hint in self.PARTS_DICT:
                    part_info = self.PARTS_DICT[part_hint]
                    parts_found.append(self._create_part_dict(
                        part_hint, part_info, 'replaced', 1, f'implied_{pattern}'
                    ))
        
        return parts_found
    
    def _create_part_dict(self, part_id: str, part_info: Dict, action: str, 
                         quantity: int, detection_method: str) -> Dict:
        """Create a standardized part dictionary"""
        return {
            'id': part_id,
            'name': part_info['name'],
            'category': part_info['category'],
            'estimated_price': part_info['avg_price'],
            'action': action,
            'quantity': quantity,
            'detection_method': detection_method
        }
    
    def _extract_quantity(self, text: str, part_keyword: str) -> int:
        """Improved quantity extraction with compiled patterns"""
        text_lower = text.lower()
        
        # Try compiled patterns first
        for pattern in self.compiled_patterns['quantity']:
            match = pattern.search(text_lower)
            if match:
                try:
                    if match.group(1):
                        return int(match.group(1))
                    elif 'all' in pattern.pattern and ('tire' in part_keyword or 'tyre' in part_keyword):
                        return 4
                    elif 'front and rear' in pattern.pattern:
                        return 2
                except (ValueError, AttributeError):
                    continue
        
        # Check for specific patterns
        specific_patterns = [
            rf'(\d+)\s+{part_keyword}s?',
            rf'{part_keyword}s?\s+(\d+)',
            rf'all\s+{part_keyword}s?',
        ]
        
        for pattern in specific_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    if match.group(1):
                        return int(match.group(1))
                    elif 'all' in pattern and ('tire' in part_keyword or 'tyre' in part_keyword):
                        return 4
                except (ValueError, AttributeError):
                    continue
        
        # Default based on part type
        if 'tire' in part_keyword or 'tyre' in part_keyword:
            # Check context for "all tires" or "4 tires"
            if re.search(r'all\s*(?:tires|tyres)', text_lower) or re.search(r'4\s*(?:tires|tyres)', text_lower):
                return 4
            return 1  # Default 1 for single tire replacement
        
        if 'brake pad' in part_keyword:
            if re.search(r'front\s+and\s+rear', text_lower):
                return 2  # 2 sets for front and rear
            if re.search(r'all\s+four', text_lower):
                return 4  # All four wheels
        
        return 1  # Default to 1
    
    def _remove_duplicate_parts(self, parts: List[Dict]) -> List[Dict]:
        """Remove duplicate parts from list while preserving order"""
        seen_ids = set()
        unique_parts = []
        
        for part in parts:
            part_id = part['id']
            if part_id not in seen_ids:
                seen_ids.add(part_id)
                unique_parts.append(part)
        
        return unique_parts
    
    def _extract_cost(self, text: str, keywords: List[str]) -> float:
        """Improved cost extraction for specific cost types"""
        text_lower = text.lower()
        
        for keyword in keywords:
            patterns = [
                rf'{keyword}\s*(?:cost|charge|fee)?\s*[:\-]?\s*[Rs$]?\s*(\d+(?:\.\d+)?)',
                rf'[Rs$]\s*(\d+(?:\.\d+)?)\s*(?:for|on)\s*{keyword}',
                rf'{keyword}\s*[Rs$]\s*(\d+(?:\.\d+)?)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1))
                    except (ValueError, AttributeError):
                        continue
        
        return 0.0
    
    def _extract_total_cost(self, text: str) -> float:
        """Improved total cost extraction with compiled patterns"""
        text_lower = text.lower()
        all_amounts = []
        
        # Use compiled patterns first
        for pattern in self.compiled_patterns['cost']:
            matches = pattern.findall(text_lower)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    # Heuristic: filter unreasonable amounts
                    if 10 <= amount <= 1000000:  # Between Rs10 and Rs1,000,000
                        all_amounts.append(amount)
                except (ValueError, AttributeError):
                    continue
        
        if all_amounts:
            # Return the largest mentioned amount (likely total)
            # But also consider the last mentioned amount
            if len(all_amounts) > 1:
                # Take the one that's mentioned with "total" or at the end
                return max(all_amounts)
            return all_amounts[0]
        
        return 0.0
    
    def _extract_odometer(self, text: str) -> Optional[int]:
        """Improved odometer extraction with compiled patterns"""
        text_lower = text.lower()
        
        for pattern in self.compiled_patterns['odometer']:
            match = pattern.search(text_lower)
            if match:
                try:
                    value = int(match.group(1))
                    # Validate reasonable odometer reading
                    if 1000 <= value <= 500000:
                        return value
                except (ValueError, AttributeError):
                    continue
        
        return None
    
    def _calculate_improved_confidence(self, text: str, parts_replaced: List, parts_repaired: List, 
                                     total_cost: float, odometer: Optional[int]) -> float:
        """Calculate improved confidence score with more factors"""
        confidence = 0.3  # Base confidence
        
        # Parts detection (up to 0.4)
        parts_count = len(parts_replaced) + len(parts_repaired)
        if parts_count > 0:
            confidence += min(0.4, parts_count * 0.15)
        
        # Cost mentioned (0.2)
        if total_cost > 0:
            confidence += 0.2
            # Bonus for reasonable cost
            if 100 <= total_cost <= 100000:
                confidence += 0.05
        
        # Odometer mentioned (0.1)
        if odometer:
            confidence += 0.1
        
        # Specific keywords that indicate good transcript (0.15)
        good_keywords = ['replaced', 'changed', 'service', 'cost', 'rupees', 'km', 'filter', 'oil', 'brake', 'tire']
        keyword_count = sum(1 for keyword in good_keywords if re.search(rf'\b{keyword}\b', text.lower()))
        confidence += min(0.15, keyword_count * 0.02)
        
        # Length of transcript indicates detail (0.1)
        word_count = len(text.split())
        if word_count > 10:
            confidence += 0.1
        elif word_count > 5:
            confidence += 0.05
        
        # Has action words (0.05)
        action_words = ['replaced', 'changed', 'fixed', 'installed', 'checked']
        if any(word in text.lower() for word in action_words):
            confidence += 0.05
        
        # Has service context (0.05)
        if any(word in text.lower() for word in ['service', 'maintenance', 'repair', 'inspection']):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _generate_detailed_work_summary(self, parts_replaced: List, parts_repaired: List, 
                                      service_type: str, total_cost: float) -> str:
        """Generate detailed work summary"""
        summary_parts = []
        
        if parts_replaced:
            part_names = []
            for p in parts_replaced:
                if p['quantity'] > 1:
                    part_names.append(f"{p['name']} (x{p['quantity']})")
                else:
                    part_names.append(p['name'])
            summary_parts.append(f"Replaced: {', '.join(part_names)}")
        
        if parts_repaired:
            part_names = [p['name'] for p in parts_repaired]
            summary_parts.append(f"Repaired: {', '.join(part_names)}")
        
        if summary_parts:
            service_name = service_type.replace('_', ' ').title()
            summary = f"{service_name}. " + ". ".join(summary_parts)
            
            if total_cost > 0:
                summary += f" Total cost: Rs{total_cost:.2f}"
            
            return summary
        
        return f"{service_type.replace('_', ' ').title()} performed"
    
    def _estimate_cost(self, parts_replaced: List, parts_repaired: List, labor_cost: float = 0) -> float:
        """Improved cost estimation with quantity consideration"""
        total = labor_cost
        
        # Parts cost
        for part in parts_replaced:
            total += part['estimated_price'] * part.get('quantity', 1)
        
        for part in parts_repaired:
            # Repairs are typically 40-60% of replacement cost
            repair_cost = part['estimated_price'] * 0.5 * part.get('quantity', 1)
            total += repair_cost
        
        # Add labor cost if not specified (30% of parts cost, minimum Rs500)
        if labor_cost == 0 and total > 0:
            labor_estimate = max(total * 0.3, 500)
            total += labor_estimate
        
        return round(total, 2)
    
    def _extract_date_info(self, text: str) -> Dict:
        """Extract date-related information"""
        date_info = {}
        text_lower = text.lower()
        
        # Today/tomorrow references
        if 'today' in text_lower:
            date_info['service_date'] = 'today'
        elif 'tomorrow' in text_lower:
            date_info['service_date'] = 'tomorrow'
        elif 'yesterday' in text_lower:
            date_info['service_date'] = 'yesterday'
        
        # Next service reminder
        if any(word in text_lower for word in ['next service', 'next maintenance', 'come back', 'return in']):
            date_info['has_next_service'] = True
        
        # Date patterns (simple)
        date_patterns = [
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
            r'(\d{1,2})\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                date_info['specific_date'] = match.group()
                break
        
        return date_info
    
    def test_accuracy(self, test_cases: List[Dict]) -> Dict:
        """Test accuracy against provided test cases"""
        results = []
        
        for test in test_cases:
            parsed = self.process_transcript(test['input'])
            
            # Calculate parts accuracy
            found_parts = set(p['name'].lower() for p in parsed['parts_replaced'] + parsed['parts_repaired'])
            expected_parts = set(p.lower() for p in test.get('expected_parts', []))
            
            if expected_parts:
                parts_accuracy = len(found_parts.intersection(expected_parts)) / len(expected_parts) * 100
            else:
                parts_accuracy = 100 if not found_parts else 0
            
            # Calculate cost accuracy
            cost_match = abs(parsed['total_cost'] - test.get('expected_cost', 0)) < 0.01
            
            results.append({
                'input': test['input'],
                'parsed': parsed,
                'expected_parts': test.get('expected_parts', []),
                'expected_cost': test.get('expected_cost', 0),
                'parts_accuracy': parts_accuracy,
                'cost_match': cost_match,
                'confidence': parsed['confidence_score']
            })
        
        # Calculate summary
        total_tests = len(results)
        avg_parts_accuracy = sum(r['parts_accuracy'] for r in results) / total_tests
        cost_accuracy = sum(1 for r in results if r['cost_match']) / total_tests * 100
        avg_confidence = sum(r['confidence'] for r in results) / total_tests
        
        return {
            'results': results,
            'summary': {
                'total_tests': total_tests,
                'average_parts_accuracy': round(avg_parts_accuracy, 2),
                'cost_accuracy': round(cost_accuracy, 2),
                'average_confidence': round(avg_confidence, 2)
            }
        }


# Example usage
if __name__ == "__main__":
    # Initialize service
    voice_service = VoiceProcessingService()
    
    # Test cases that were failing
    test_cases = [
        {
            "input": "Changed oil filter and engine oil for 1200 rupees at 15000 km",
            "expected_parts": ["Engine Oil", "Oil Filter"],
            "expected_cost": 1200
        },
        {
            "input": "Replaced brake pads front and rear, total 3000 rupees",
            "expected_parts": ["Brake Pads"],
            "expected_cost": 3000
        },
        {
            "input": "Full service with air filter, oil filter, engine oil change. 2500 rupees",
            "expected_parts": ["Air Filter", "Oil Filter", "Engine Oil"],
            "expected_cost": 2500
        }
    ]
    
    # Run tests
    print("🧪 Testing Voice Processing Service")
    print("=" * 60)
    
    for test in test_cases:
        result = voice_service.process_transcript(test['input'])
        
        print(f"\n📝 Test: {test['input']}")
        print(f"   Found parts: {result['raw_parts_found']}")
        print(f"   Expected parts: {test['expected_parts']}")
        
        # Calculate accuracy
        found_set = set(p.lower() for p in result['raw_parts_found'])
        expected_set = set(p.lower() for p in test['expected_parts'])
        if expected_set:
            accuracy = len(found_set.intersection(expected_set)) / len(expected_set) * 100
        else:
            accuracy = 100 if not found_set else 0
        
        print(f"   Parts accuracy: {accuracy:.1f}%")
        print(f"   Found cost: Rs{result['total_cost']}")
        print(f"   Expected cost: Rs{test['expected_cost']}")
        print(f"   Cost accuracy: {'✓' if abs(result['total_cost'] - test['expected_cost']) < 0.01 else '✗'}")
        print(f"   Confidence: {result['confidence_score']:.2f}")
        
        if accuracy >= 80:
            print("   ✅ Good!")
        elif accuracy >= 50:
            print("   ⚠️  Fair")
        else:
            print("   ❌ Needs improvement")