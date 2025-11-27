"""
Credential Matching Service
Maps scholarship requirements to available student credentials
"""

import re
from typing import List, Dict, Tuple, Optional

class CredentialMatcher:
    """Service to match scholarship requirements with student credentials"""
    
    # Mapping of common requirement patterns to credential types
    REQUIREMENT_MAPPINGS = {
        # Photos and IDs
        'photo_2x2': ['Recent 2x2 or passport-size photo'],
        'valid_id': ['Valid School ID or any government-issued ID', 'Valid ID', 'Driver\'s License', 'National ID'],
        
        # Academic Documents
        'enrollment_cert': ['Certificate of Enrollment', 'Enrollment Certificate'],
        'report_card': ['Report Card / Transcript of Records (TOR)', 'Transcript of Records', 'Latest Report Card', 'Grades'],
        'good_moral': ['Certificate of Good Moral Character', 'Good Moral Certificate'],
        
        # Recommendation and Awards
        'recommendation_letter': ['Recommendation Letter', 'Letter of Recommendation'],
        'honors_awards': ['Honors or Awards Certificates', 'Academic Awards', 'Academic Awards/Certificates'],
        
        # Financial Documents
        'indigency_cert': ['Certificate of Indigency', 'Indigency Certificate'],
        'itr': ['Parents\' or Guardians\' Income Tax Return (ITR)', 'Income Tax Return', 'ITR'],
        'proof_income': ['Proof of Income', 'Income Proof', 'Salary Certificate'],
        
        # Residency and Identity
        'barangay_clearance': ['Barangay Clearance or Residency Certificate', 'Barangay Certificate', 'Residency Certificate'],
        'birth_cert': ['Birth Certificate (PSA or NSO)', 'Birth Certificate', 'Certificate of Birth'],
        
        # Medical
        'medical_cert': ['Medical Certificate', 'Health Certificate', 'Medical Clearance']
    }
    
    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Normalize text for better matching"""
        if not text:
            return ""
        return re.sub(r'[^\w\s]', '', text.lower().strip())
    
    @classmethod
    def find_matching_credentials(cls, requirements: List[str], available_credentials: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Find matching credentials for each requirement
        
        Args:
            requirements: List of requirement strings from scholarship
            available_credentials: List of credential dictionaries with 'credential_type' field
            
        Returns:
            Dictionary mapping requirement to list of matching credentials
        """
        matches = {}
        
        for requirement in requirements:
            requirement = requirement.strip()
            if not requirement:
                continue
                
            matching_creds = []
            normalized_req = cls.normalize_text(requirement)
            
            # First, check if this is a short code that maps to descriptive names
            if requirement in cls.REQUIREMENT_MAPPINGS:
                # This is a short code (like 'photo_2x2'), get the descriptive names
                credential_types = cls.REQUIREMENT_MAPPINGS[requirement]
                for cred in available_credentials:
                    cred_type_normalized = cls.normalize_text(cred.get('credential_type', ''))
                    for cred_type in credential_types:
                        cred_type_normalized_mapping = cls.normalize_text(cred_type)
                        # More precise matching - check if the credential type exactly matches or is contained in the mapping
                        if (cred_type_normalized_mapping == cred_type_normalized or 
                            cred_type_normalized_mapping in cred_type_normalized):
                            if cred not in matching_creds:
                                matching_creds.append(cred)
                                break  # Only add once per credential
            else:
                # This is a descriptive requirement, try direct mapping lookup
                for pattern, credential_types in cls.REQUIREMENT_MAPPINGS.items():
                    if cls.normalize_text(pattern) in normalized_req or normalized_req in cls.normalize_text(pattern):
                        for cred in available_credentials:
                            cred_type_normalized = cls.normalize_text(cred.get('credential_type', ''))
                            for cred_type in credential_types:
                                if cls.normalize_text(cred_type) in cred_type_normalized:
                                    if cred not in matching_creds:
                                        matching_creds.append(cred)
            
            # Fuzzy matching for unmatched requirements
            if not matching_creds:
                for cred in available_credentials:
                    cred_type = cred.get('credential_type', '')
                    if cls._calculate_similarity(normalized_req, cls.normalize_text(cred_type)) > 0.6:
                        matching_creds.append(cred)
            
            matches[requirement] = matching_creds
        
        return matches
    
    @classmethod
    def _calculate_similarity(cls, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    @classmethod
    def get_requirement_status(cls, requirement: str, available_credentials: List[Dict]) -> Tuple[str, Optional[Dict]]:
        """
        Get status of a requirement based on available credentials
        
        Returns:
            Tuple of (status, best_match_credential)
            Status: 'available', 'missing', 'multiple'
        """
        matches = cls.find_matching_credentials([requirement], available_credentials)
        matching_creds = matches.get(requirement, [])
        
        if not matching_creds:
            return 'missing', None
        elif len(matching_creds) == 1:
            return 'available', matching_creds[0]
        else:
            # Return the most recent credential
            best_match = max(matching_creds, key=lambda x: x.get('upload_date', ''))
            return 'multiple', best_match
    
    @classmethod
    def suggest_credential_type(cls, requirement: str) -> str:
        """Suggest the most appropriate credential type for a requirement"""
        # First check if this is a short code
        if requirement in cls.REQUIREMENT_MAPPINGS:
            return cls.REQUIREMENT_MAPPINGS[requirement][0]  # Return first descriptive name
        
        normalized_req = cls.normalize_text(requirement)
        
        # Find best matching credential type
        best_match = ""
        best_score = 0
        
        for pattern, credential_types in cls.REQUIREMENT_MAPPINGS.items():
            pattern_normalized = cls.normalize_text(pattern)
            similarity = cls._calculate_similarity(normalized_req, pattern_normalized)
            
            if similarity > best_score:
                best_score = similarity
                best_match = credential_types[0]  # Use first credential type as suggestion
        
        return best_match if best_score > 0.3 else requirement
