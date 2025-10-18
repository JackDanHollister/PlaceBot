#!/usr/bin/env python3
"""
AI Processor with Anthropic Prompt Caching Implementation
================================================================

"""

import json
import re
import requests
import time
from typing import Dict, List, Optional, Any


class AIProcessor:
    """Handles AI processing with proper Anthropic prompt caching."""
    
    def __init__(self, model_config: Dict[str, Any]):
        """Initialize AI processor with model configuration."""
        self.model_config = model_config
        self.api_key = model_config.get('api_key', '')
        self.requests_per_minute = model_config.get('requests_per_minute', 50)
        self.last_request_time = 0
        
        # Determine caching type based on model
        provider = model_config.get('name', '').lower()
        self.use_claude_caching = 'claude' in provider and 'cached' in provider
        self.use_gemini_caching = 'gemini' in provider and 'cached' in provider
        self.use_caching = self.use_claude_caching or self.use_gemini_caching
        
        # Initialize caching
        self.cached_instructions_message = None  # For Claude
        self.gemini_cached_content_name = None   # For Gemini
        
        cache_type = "Claude" if self.use_claude_caching else "Gemini" if self.use_gemini_caching else "None"
        print(f"AI Processor initialized - Caching: {'SUCCESS ' + cache_type if self.use_caching else 'ERROR Disabled'}")
    
    def _rate_limit(self):
        """Apply rate limiting between API requests."""
        if self.requests_per_minute > 0:
            min_interval = 60 / self.requests_per_minute
            elapsed = time.time() - self.last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
    
    def _get_gemini_cached_content(self):
        """Create and get Gemini cached content (create once, reuse for all calls)."""
        if self.gemini_cached_content_name is None:
            instructions = self._get_full_instructions()
            
            try:
                print("Making Creating Gemini cache...")
                
                # Get model configuration
                model_module = self.model_config.get('module')
                if not model_module or not hasattr(model_module, 'format_cache_request'):
                    print("ERROR Gemini caching not supported for this model configuration")
                    return None
                
                # Create cache request
                cache_request = model_module.format_cache_request(instructions)
                
                # Make cache creation request
                headers = model_module.get_cache_headers(self.api_key)
                cache_endpoint = getattr(model_module, 'CACHE_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/cachedContents')
                
                response = requests.post(
                    cache_endpoint,
                    headers=headers,
                    json=cache_request,
                    timeout=60
                )
                
                if response.status_code == 200:
                    cache_data = response.json()
                    self.gemini_cached_content_name = cache_data.get('name', '')
                    
                    print(f"SUCCESS Gemini cache created: {self.gemini_cached_content_name}")
                    
                    # Log cache details
                    usage = cache_data.get('usageMetadata', {})
                    if usage:
                        print(f"   📊 Cached tokens: {usage.get('totalTokenCount', 0)}")
                        
                    expire_time = cache_data.get('expireTime', '')
                    if expire_time:
                        print(f"   ⏰ Expires: {expire_time}")
                        
                else:
                    print(f"ERROR Failed to create Gemini cache: {response.status_code}")
                    print(f"   Error: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"ERROR Gemini cache creation failed: {str(e)}")
                return None
        
        return self.gemini_cached_content_name
    
    def _get_full_instructions(self):
        """Get the full instruction text used by both Claude and Gemini."""
        return """Parse this museum specimen locality into standardized geographic hierarchy and georeference the locality.

**CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown, no additional text - just the JSON object.**

## PROCESSING APPROACH

You are a specialist in standardizing museum specimen locality data. Your primary objectives are:
- **Accuracy over creativity**: Follow the standardization rules precisely
- **Consistency**: Apply the same parsing logic to similar locality patterns  
- **Preservation**: Never lose information - capture uncertain data rather than omit it
- **Standardization**: Convert varied input formats to consistent output structure
- **Documentation**: Record your parsing decisions in the notes fields

Prioritize systematic rule-following over interpretive analysis.

## CRITICAL COORDINATE PRESERVATION RULES (HIGHEST PRIORITY)

**NEVER OVERWRITE PROVIDED COORDINATES**
- IF EXISTING DECIMAL COORDINATES ARE PROVIDED: Use them exactly as given, DO NOT estimate new ones
- IF DMS COORDINATES ARE PROVIDED: Convert to decimal and mark as "coordinates_extracted"  
- IF GRID REFERENCE CONVERTED COORDINATES ARE PROVIDED: Use them exactly as given
- IF ELEVATION-ONLY DATA: Do not confuse elevation values with coordinates
- ONLY estimate coordinates if NO existing coordinates are provided anywhere in the context
- When preserving coordinates, mark coordinate_source appropriately

## 🚨 COMPLEX LOCALITY PARSING RULES

### Multi-Part Locality Processing
- **Pattern Recognition**: Localities containing multiple geographic references separated by:
  - Semicolons, commas, or other delimiters
  - Explicit labels ("1st label:", "Site A:", "Location 1:")
  - Conjunctions ("and", "also", "near")
  - Sequential geographic hierarchy

- **Selection Strategy**: 
  1. **Identify all geographic components** in the locality string
  2. **Rank by specificity**: Landmarks > Towns > Regions > Countries
  3. **Choose most specific location** for coordinate estimation
  4. **Use broader components** for geographic hierarchy

- **Processing Examples**:
  - "1st label: Uganda, Gulu Dr., W. Nile; 2nd label: Bududiri, Mt. Elgon, 4,200 ft."
    → Focus on "Mt. Elgon" (most specific landmark)
  - "Tanzania, Arusha region, near Kilimanjaro, site 5"
    → Focus on "Kilimanjaro" coordinates
  - "Multiple locations: Forest A; Grassland B; near River C"
    → Focus on "River C" if most specific, or choose primary location

### Complex Geographic References
- **Distance + Direction**: "20 m. W. Kampala", "5km north of Darwin"
- **Relative Positioning**: "between X and Y", "halfway to Z"
- **Alternative Names**: "Location A (also called B)", "X [= modern Y]"
- **Site Collections**: "Sites 1-5 near landmark", "transect from A to B"

### Country Name De-prioritization
- **Critical Rule**: NEVER default to country-center coordinates for complex localities
- **Country Mention Handling**: If country appears with specific places, focus on the specific places
- **Fallback Prevention**: Even if uncertain about specific location, estimate regional coordinates rather than country-center
- **Quality Control**: Country-center coordinates should only be used as absolute last resort

### Distance + Direction + Place Combinations
- **Format Recognition**: "20 m. W. Kampala", "5km north of Darwin", "30 meters east of bridge"
- **Coordinate Strategy**: Calculate offset from the named place, NOT country center
- **Processing Steps**:
  1. Identify the base location (e.g., "Kampala", "Darwin")
  2. Calculate approximate coordinates for that specific place
  3. Apply distance/direction offset if possible
  4. Use appropriate radius to reflect uncertainty

## TEXT PREPROCESSING AND CHARACTER ENCODING

### Character Encoding Issues
- Convert corrupted characters: "Â°" → "°", "Ã©" → "é", "Ã¡" → "á"
- Handle common encoding artifacts from OCR or database imports
- Normalize Unicode characters to standard forms
- Convert HTML entities: "&deg;" → "°", "&amp;" → "&"

### Text Cleaning Rules
- Remove leading/trailing whitespace and normalize internal spacing
- Handle mixed character sets (Latin, Cyrillic, Arabic, etc.)
- Preserve original diacritics but note simplified versions
- Flag potentially corrupted text for manual review


## GEOGRAPHIC HIERARCHY STANDARDIZATION

### Hierarchy Levels (Most to Least Specific)
1. **Country**: Full, unabbreviated name of the country, major political unit, or ocean
   - Use provided Country field if available, otherwise determine from locality
   - Expand abbreviations: "Hispan." → "Spain", "Germ." → "Germany"
   - Historical names: "MAGYARORSZAG [= Hungary]" → "Hungary"

2. **State**: Full name of state, province, territory, or prefecture (next level below country)
   - FOR UK: Use "England", "Scotland", "Wales", "Northern Ireland" (NOT "United Kingdom")
   - FOR SPAIN: Use province names like "Andalusia", "Catalonia", "Valencia"
   - FOR GERMANY: Use state names like "Bavaria", "Saxony", "Thuringia"
   - FOR ITALY: Use region names like "Tuscany", "Lombardy", "Sicily"

3. **Region**: County, shire, municipality, department, or park (next level below state)
   - **UK Priority**: Use Vice County names when VC codes present
   - **Modern counties**: "Co." → "County", "Hunts." → "Huntingdonshire" 
   - **Vice Counties**: "VC 11" → "South Hampshire", "VC 25" → "East Suffolk"
   - **Conflicts**: When modern county differs from VC, use VC name in region, note modern county
   - French departments: "B.Alp" → "Basses-Alpes", "Pyr. or." → "Pyrénées-Orientales"
   - German regions: Expand abbreviated forms

4. **Sector**: Named conservation areas, parks, forests, lakes, or large geographic features
   - National parks, nature reserves, forests, major lakes
   - Large geographic features like mountain ranges
   - NOT small villages or towns (those go in exact_site)

5. **Exact Site**: Specific locality details within the sector/region
   - Include ONLY details NOT captured in higher hierarchy levels
   - Include: landmarks, habitat descriptions, distances, directions, grid references
   - EXCLUDE: elevation (goes to elevation field), administrative areas, coordinates

## COORDINATE PROCESSING SYSTEM

### Source Priority Ranking
1. **"grid_reference_converted"** - Converted from grid reference (MOST ACCURATE)
2. **"coordinates_provided"** - Direct decimal lat/long coordinates given
3. **"coordinates_extracted"** - Extracted/converted from DMS format in text
4. **"estimated"** - Estimated from place names (LEAST ACCURATE)

### Coordinate Recognition Patterns
- **Decimal degrees**: 12.345678, -98.765432
- **DMS formats**: 27°59'34.7"N 15°22'10.9"W
- **Grid references**: SK4480, TL563705, TQ6666
- **UTM coordinates**: 33T 06266 52874

### Enhanced Coordinate Radius Estimation Guidelines (Only if NO coordinates provided)
- If coordinates are provided do not give a radius
- **Specific landmarks/buildings**: 500-1000m radius
- **Towns/villages**: 2000-3000m radius  
- **Major cities**: 5000-10000m radius
- **Nature reserves/parks**: 2000-5000m radius
- **Mountains/peaks**: 1000-3000m radius
- **Regional estimates**: 10000-50000m radius
- **Country-level fallback**: 100000m+ radius (AVOID THIS - use only as absolute last resort)

### Coordinate Quality Indicators
- **High specificity**: Named buildings, landmarks, grid references
- **Medium specificity**: Towns, villages, specific geographic features
- **Low specificity**: Regional descriptions, administrative areas only
- **Unacceptable**: Country-center coordinates for specific locality descriptions


## ABBREVIATION EXPANSION RULES

### Country Abbreviations
- Hispan./Hispania → Spain
- Germ./Germania → Germany  
- Ital./Italia → Italy
- Graecia/Grecia → Greece
- Gallia → France
- Hunts. → Huntingdonshire
- Bucks → Buckinghamshire
- Heref./Herefs. → Herefordshire
- Aberdeens. → Aberdeenshire

### Administrative Regions  
- Co. → County
- Prov./Pr. → Province
- Dept. → Department
- Distr. → District
- VC → Vice County

### Geographic Features
- Mt./Mts. → Mount/Mountains  
- R. → River
- L./Lk. → Lake
- Is./Isl. → Island/Islands
- Pt. → Point

## MARITIME AND BOUNDARY REGIONS

### Maritime Locations
- **Coastal Features**: Distinguish land vs water features
- **Islands**: Archipelago vs individual island naming
- **Offshore**: Distance and direction from mainland
- **Exclusive Economic Zones**: Maritime boundaries

### Border Regions
- **Disputed Territories**: Use internationally recognized boundaries
- **Cross-border Features**: Rivers, mountain ranges
- **Administrative Changes**: Account for boundary modifications

## UK VICE COUNTY PROCESSING

### Vice County Recognition Patterns
- **Standard formats**: "VC1", "VC 1", "VC12", "VC 12"
- **In text**: "Somerset, VC 5", "Hants, VC11", "Dorset VC9"
- **Standalone**: "VC 25" (when county name missing)

### Vice County Lookup
VC1=West Cornwall, VC2=East Cornwall, VC3=South Devon, VC4=North Devon, VC5=South Somerset, VC6=North Somerset, VC7=North Wiltshire, VC8=South Wiltshire, VC9=Dorset, VC10=Isle of Wight, VC11=South Hampshire, VC12=North Hampshire, VC13=West Sussex, VC14=East Sussex, VC15=East Kent, VC16=West Kent, VC17=Surrey, VC18=South Essex, VC19=North Essex, VC20=Hertfordshire, VC21=Middlesex, VC22=Berkshire, VC23=Oxfordshire, VC24=Buckinghamshire, VC25=East Suffolk, VC26=West Suffolk, VC27=East Norfolk, VC28=West Norfolk, VC29=Cambridgeshire, VC30=Bedfordshire, VC31=Huntingdonshire, VC32=Northamptonshire, VC33=East Gloucestershire, VC34=West Gloucestershire, VC35=Monmouthshire, VC36=Herefordshire, VC37=Worcestershire, VC38=Warwickshire, VC39=Staffordshire, VC40=Shropshire, VC41=Glamorgan, VC42=Breconshire, VC43=Radnorshire, VC44=Carmarthenshire, VC45=Pembrokeshire, VC46=Cardiganshire, VC47=Montgomeryshire, VC48=Merionethshire, VC49=Caernarvonshire, VC50=Denbighshire, VC51=Flintshire, VC52=Anglesey, VC53=South Lincolnshire, VC54=North Lincolnshire, VC55=Leicestershire, VC56=Nottinghamshire, VC57=Derbyshire, VC58=Cheshire, VC59=South Lancashire, VC60=West Lancashire, VC61=South-east Yorkshire, VC62=North-east Yorkshire, VC63=South-west Yorkshire, VC64=Mid-west Yorkshire, VC65=North-west Yorkshire, VC66=County Durham, VC67=South Northumberland, VC68=North Northumberland, VC69=Westmorland, VC70=Cumberland, VC71=Isle of Man, VC72=Dumfriesshire, VC73=Kirkcudbrightshire, VC74=Wigtownshire, VC75=Ayrshire, VC76=Renfrewshire, VC77=Lanarkshire, VC78=Peeblesshire, VC79=Selkirkshire, VC80=Roxburghshire, VC81=Berwickshire, VC82=East Lothian, VC83=Midlothian, VC84=West Lothian, VC85=Fifeshire, VC86=Stirlingshire, VC87=West Perthshire, VC88=Mid Perthshire, VC89=East Perthshire, VC90=Angus, VC91=Kincardineshire, VC92=South Aberdeenshire, VC93=North Aberdeenshire, VC94=Banffshire, VC95=Moray, VC96=East Inverness-shire, VC97=West Inverness-shire, VC98=Argyll, VC99=Dunbartonshire, VC100=Clyde Isles, VC101=Kintyre, VC102=South Ebudes, VC103=Mid Ebudes, VC104=North Ebudes, VC105=West Ross, VC106=East Ross, VC107=East Sutherland, VC108=West Sutherland, VC109=Caithness, VC110=Outer Hebrides, VC111=Orkney, VC112=Shetland, VC113=Channel Islands

### Processing Rules
- **When VC found**: Use VC name as the primary region identifier
- **Modern county vs VC**: Prefer VC name for historical accuracy
- **Multiple counties**: If modern county differs from VC, note both
- **Missing VC name**: Look up number and use full VC name
- **VC in exact_site**: Move to region field, note VC number in notes

### Examples of VC Processing
- "Hants, VC 11" → region: "South Hampshire", notes: "VC 11"
- "VC 25" → region: "East Suffolk", notes: "VC 25 (county name inferred)"
- "Somerset, VC 5" → region: "South Somerset", notes: "VC 5"

## ELEVATION PROCESSING

### Extraction Rules
- Convert feet to meters: multiply by 0.3048
- Single values: "elevation 450m" → elevation_meters: 450
- Ranges: "1000-1400ft" → use midpoint in meters, note range in Collection Notes
- Preserve original format in elevation_original field

### Elevation vs Coordinate Confusion Prevention
- Elevations are typically 0-9000m (0-30000ft)
- Coordinates have specific lat/long ranges
- Grid references have letter prefixes (UK) or specific formats

## EXACT SITE CONTENT RULES

### INCLUDE in exact_site:
- Specific landmarks: "near old oak tree", "beside bridge"
- Habitat descriptions: "roadside verge", "south-facing slope", "rocky outcrop"
- Relative positions: "500m north of named place", "2km west of town center"  
- Microhabitats: "car park area", "visitor center grounds", "stream bank"
- Grid references: "grid ref SK4480" (ALWAYS ADD "grid ref" as a prefix)
- Site codes: "Site 1", "Plot A", "Station 23"
- Specific buildings/structures: "lighthouse", "church", "mill"
- named places

### EXCLUDE from exact_site:
- Administrative areas (already in hierarchy)
- Elevation data (goes to Elevation field)
- Coordinate data (processed separately)
- Country/state/region names
- Large geographic features (go in Sector field)
- Vice County (goes in Region field)

## HISTORICAL AND LINGUISTIC PROCESSING
Museum specimens often have historical place names. Translate these to modern equivalents.
### Historical Name Handling
- Format: "historical [= modern]" 
- Example: "Abbazia [=Opatija]" → use "Opatija" in hierarchy and add Abbazia to "collection notes" field
- Preserve historical context in "collection notes" field

### Non-English Locality Processing
- Translate major administrative divisions to English
- Keep specific place names in original language
- Note language variants: "Breslau [=Wrocław]"

### Uncertain/Damaged Text
- Mark with "?" in original: "Asia min. ?"
- Preserve uncertainty in confidence rating
- Don't guess at abbreviations

### Notes Field Content
- Abbreviations expanded with source abbreviations
- Vice County numbers: "VC 11", "VC 25" 
- Modern vs historical county differences
- Coordinate estimation methods
- Grid reference conversions
- Processing decisions and assumptions

## CONFIDENCE ASSESSMENT MATRIX

### High Confidence
- Grid reference provided and converted
- Precise coordinates provided  
- Well-known, unambiguous locations
- Complete administrative hierarchy
- No abbreviations or uncertainty markers

### Medium Confidence  
- Coordinates extracted from DMS
- Known locations with minor ambiguity
- Some abbreviations expanded with certainty
- Partial administrative hierarchy

### Low Confidence
- Estimated coordinates only
- Significant abbreviations or uncertainty
- Ambiguous or incomplete location data
- Historical names without modern equivalents

## EDGE CASE HANDLING

### Multiple Locations in Single String
- Use primary/most specific location
- Note alternatives in Collection Notes
- Choose most precise coordinates

### Waterways and Marine Locations
- Ocean/sea names go in country field
- Coastal features in region/sector
- Ship positions: use coordinates if provided

### Border Regions and Disputed Areas
- Use modern political boundaries
- Note historical context if relevant
- Choose most appropriate current country

### Archaeological/Historical Sites
- Use current geographic names
- Note historical significance
- Apply modern coordinate system

## OUTPUT FORMAT SPECIFICATION

```json
{
  "country": "Full, standardized country name",
  "state": "Province/state/territory (standardized)",
  "region": "County/shire/municipality (expanded from abbreviations)",
  "sector": "Conservation area/park/major geographic feature",
  "exact_site": "Specific site details, landmarks, habitat - NO admin areas or elevation",
  "latitude": 12.345678,
  "longitude": -98.765432,
  "coordinate_source": "grid_reference_converted|coordinates_provided|coordinates_extracted|estimated",
  "coordinate_radius_meters": 2000,
  "elevation_meters": 123.4,
  "elevation_original": "405ft elevation",
  "confidence": "high|medium|low",
  "notes": "Abbreviations expanded, processing decisions, uncertainty notes",
  "collection_notes": "Elevation ranges, alternative locations, additional context"
}
```

## FIELD SEPARATION EXAMPLES

### Example 1: Complete UK Locality
**INPUT**: "Wicken Fen Nature Reserve, Cambridgeshire, England, beside boardwalk near tower, elevation 5m, grid ref TL563705"

**OUTPUT**:
```json
{
  "country": "United Kingdom",
  "state": "England", 
  "region": "Cambridgeshire",
  "sector": "Wicken Fen Nature Reserve",
  "exact_site": "beside boardwalk near tower, grid ref TL563705",
  "latitude": 52.30127,
  "longitude": 0.29147,
  "coordinate_source": "grid_reference_converted",
  "coordinate_radius_meters": 1000,
  "elevation_meters": 5,
  "elevation_original": "elevation 5m",
  "confidence": "high",
  "notes": "Grid reference TL563705 converted to coordinates",
  "collection_notes": ""
}
```

### Example 2: Historical European Locality  
**INPUT**: "Holbrook (S), South Yorkshire, SK4480, roadside, 200ft elevation"

**OUTPUT**:
```json
{
  "country": "United Kingdom",
  "state": "England",
  "region": "South Yorkshire", 
  "sector": "",
  "exact_site": "Holbrook (S), roadside, grid ref SK4480",
  "latitude": 53.28124,
  "longitude": -1.31456,
  "coordinate_source": "grid_reference_converted", 
  "coordinate_radius_meters": 2000,
  "elevation_meters": 61,
  "elevation_original": "200ft elevation",
  "confidence": "high",
  "notes": "Grid reference SK4480 converted, elevation converted from feet",
  "collection_notes": ""
}
```

### Example 3: Coordinate Preservation
**INPUT**: "Gran Canaria rockpools in Taliarte, lighthouse 27°59'34.7'N 15°22'10.9'W"

**OUTPUT**:
```json
{
  "country": "Spain",
  "state": "Canary Islands",
  "region": "Las Palmas",
  "sector": "Gran Canaria",
  "exact_site": "rockpools in Taliarte, lighthouse",
  "latitude": 27.992972,
  "longitude": -15.369694,
  "coordinate_source": "coordinates_extracted",
  "coordinate_radius_meters": 500,
  "elevation_meters": null,
  "elevation_original": "",
  "confidence": "high",
  "notes": "DMS coordinates converted to decimal degrees",
  "collection_notes": ""
}
```

### Example 4: Vice County Processing
**INPUT**: "Wicken Fen, Cambs., VC 29"

**OUTPUT**:
```json
{
  "country": "United Kingdom",
  "state": "England", 
  "region": "Cambridgeshire",
  "sector": "Wicken Fen",
  "exact_site": "",
  "latitude": 52.3013,
  "longitude": 0.2915,
  "coordinate_source": "estimated",
  "coordinate_radius_meters": 2000,
  "elevation_meters": null,
  "elevation_original": "",
  "confidence": "medium",
  "notes": "VC 29 (Cambridgeshire), modern county matches VC",
  "collection_notes": ""
}
```

## PROCESSING CHECKLIST

Before finalizing output, verify:
- [ ] Coordinates preserved if provided (never estimated over existing)
- [ ] All abbreviations expanded appropriately  
- [ ] **UK Vice Counties processed and looked up correctly**
- [ ] **VC numbers noted in notes field**
- [ ] Elevation separated from coordinates correctly
- [ ] Administrative hierarchy follows country-specific rules
- [ ] Exact_site contains only specific locality details
- [ ] Confidence rating matches data quality
- [ ] Historical names handled appropriately
- [ ] Grid references noted for reference
"""
    
    def _get_cached_instructions(self):
        """Get cached instructions message for Claude (create once, reuse for all calls)."""
        if self.cached_instructions_message is None:
            instructions = self._get_full_instructions()
            
            self.cached_instructions_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": instructions,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
        
        return self.cached_instructions_message
    
    def _build_prompt(self, locality: str, country: str, coordinate_context: str = "") -> str:
        """Build traditional prompt for non-cached models."""
        instructions = self._get_full_instructions()
        
        return f"""{instructions}

Locality: "{locality}"
Country: {country if country else "[Not provided - please determine from locality text]"}{coordinate_context}

Respond with JSON only."""
    
    def _prepare_coordinate_context(self, locality: str, converted_lat: Optional[float], 
                                  converted_lon: Optional[float], coord_source: str, 
                                  coord_radius: Optional[float] = None) -> str:
        """Prepare coordinate context for the AI prompt."""
        if converted_lat and converted_lon:
            if coord_source == "coordinates_provided":
                return f"\n\nEXISTING COORDINATES: {converted_lat:.6f}, {converted_lon:.6f} (PRESERVE THESE EXACT COORDINATES - do not overwrite)"
            elif coord_source == "grid_reference_converted":
                from .coordinate_utils import detect_grid_references
                detected_grids = detect_grid_references(locality)
                context = f"\n\nGRID REFERENCE CONVERTED: {', '.join(detected_grids)} -> {converted_lat:.6f}, {converted_lon:.6f}"
                if coord_radius:
                    context += f"\nPRECISION RADIUS: {coord_radius:.1f} meters (use this for coordinate_radius_meters field)"
                context += "\nIMPORTANT: PRESERVE these mathematically converted coordinates, do not estimate or overwrite!"
                return context
        
        return "\n\nNO EXISTING COORDINATES: Please estimate coordinates from locality if possible"
    
    def _make_api_request(self, locality: str, country: str, coordinate_context: str = "", max_retries: int = 5) -> Dict[str, Any]:
        """Make API request - cached for Claude, traditional for others."""
        
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                if self.use_claude_caching:
                    # CLAUDE CACHED REQUEST
                    print(f"Making Making cached Claude API request (attempt {attempt + 1})")
                    
                    # Build messages array exactly like colleague's example
                    messages = [
                        self._get_cached_instructions(),
                        {
                            "role": "user", 
                            "content": f"Please georeference this locality string: {locality}\nCountry: {country}{coordinate_context}"
                        }
                    ]
                    
                    headers = {
                        'x-api-key': self.api_key,
                        'Content-Type': 'application/json',
                        'anthropic-version': '2023-06-01'
                    }
                    
                    request_body = {
                        'model': self.model_config.get('model_id', 'claude-3-haiku-20240307'),
                        'max_tokens': self.model_config.get('max_output_tokens', 1000),
                        'messages': messages
                    }
                    
                    endpoint = self.model_config.get('api_endpoint', 'https://api.anthropic.com/v1/messages')
                    
                elif self.use_gemini_caching:
                    # GEMINI CACHED REQUEST
                    print(f"Making Making cached Gemini API request (attempt {attempt + 1})")
                    
                    # Get or create cache
                    cached_content_name = self._get_gemini_cached_content()
                    if not cached_content_name:
                        print("ERROR Failed to get Gemini cache, falling back to traditional request")
                        self.use_gemini_caching = False
                        return self._make_api_request(locality, country, coordinate_context, max_retries)
                    
                    # Get model module for request formatting
                    model_module = self.model_config.get('module')
                    if not model_module:
                        print("ERROR No model module found for Gemini caching")
                        return {'success': False, 'error': 'No model module found'}
                        
                    headers = model_module.get_headers(self.api_key)
                    
                    # Format prompt
                    prompt = f"Please georeference this locality string: {locality}\nCountry: {country}{coordinate_context}"
                    
                    # Use cached content in request
                    request_body = model_module.format_request(
                        prompt, 
                        self.model_config.get('max_output_tokens', 500),
                        cached_content_name
                    )
                    
                    endpoint = self.model_config.get("api_endpoint", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent")
                    
                else:
                    # TRADITIONAL REQUEST (for non-Claude models)
                    print(f"Making Making traditional API request (attempt {attempt + 1})")
                    
                    model_module = self.model_config.get('module')
                    if model_module and hasattr(model_module, 'get_headers'):
                        headers = model_module.get_headers(self.api_key)
                        prompt = self._build_prompt(locality, country, coordinate_context)
                        request_body = model_module.format_request(prompt, self.model_config.get('max_output_tokens', 500))
                    else:
                        headers = {
                            'x-api-key': self.api_key,
                            'Content-Type': 'application/json',
                            'anthropic-version': '2023-06-01'
                        }
                        prompt = self._build_prompt(locality, country, coordinate_context)
                        request_body = {
                            'model': self.model_config.get('model_id', 'claude-3-haiku-20240307'),
                            'max_tokens': self.model_config.get('max_output_tokens', 500),
                            'messages': [{'role': 'user', 'content': prompt}]
                        }
                    
                    endpoint = self.model_config.get('api_endpoint', 'https://api.anthropic.com/v1/messages')
                
                # Make the request
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=request_body,
                    timeout=30
                )
                
                print(f"API Response: {response.status_code}")
                
                if response.status_code == 200:
                    return {'success': True, 'data': response.json()}
                elif (response.status_code == 429 or response.status_code == 500 or response.status_code == 529) and attempt < max_retries:
                    # Handle rate limits (429), internal errors (500), and overloaded (529) errors
                    if response.status_code == 500:
                        # Internal server error - retry with exponential backoff
                        wait_time = (2 ** attempt) * 4
                        error_type = "Internal server error (500)"
                    elif response.status_code == 529:
                        # Server overloaded - longer wait times
                        wait_time = (2 ** attempt) * 5
                        error_type = "Server overloaded"
                    else:
                        # Rate limit - standard wait
                        wait_time = (2 ** attempt) * 3  
                        error_type = "Rate limit"
                    print(f"Waiting {error_type} hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    error_details = response.text if hasattr(response, 'text') else 'No details'
                    print(f"ERROR API Error {response.status_code}: {error_details}")
                    return {'success': False, 'error': f'API error: {response.status_code}', 'details': error_details}
                    
            except Exception as e:
                print(f"ERROR Request exception: {str(e)}")
                if attempt < max_retries:
                    print(f"Waiting Retrying {attempt + 1}/{max_retries}")
                    time.sleep(2)
                    continue
                return {'success': False, 'error': f'Request failed: {str(e)}'}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    def _extract_token_usage(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract token usage information from API response (vendor-specific)."""
        token_info = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'token_source': 'unknown'
        }
        
        try:
            # Claude format: usage.input_tokens, usage.output_tokens, cache data
            if 'usage' in response_data and 'input_tokens' in response_data['usage']:
                usage = response_data['usage']
                token_info.update({
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                    'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
                    'token_source': 'claude',
                    # Cache-specific token data for Anthropic Claude
                    'cache_creation_input_tokens': usage.get('cache_creation_input_tokens', 0),
                    'cache_read_input_tokens': usage.get('cache_read_input_tokens', 0)
                })
            
            # OpenAI format: usage.prompt_tokens, usage.completion_tokens, usage.total_tokens + caching
            elif 'usage' in response_data and 'prompt_tokens' in response_data['usage']:
                usage = response_data['usage']
                token_info.update({
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0),
                    'token_source': 'openai',
                    # OpenAI Cache Detection - prompt_tokens_details.cached_tokens
                    'cached_tokens': usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
                })
            
            # Gemini format: usageMetadata.promptTokenCount, usageMetadata.candidatesTokenCount + caching
            elif 'usageMetadata' in response_data:
                usage = response_data['usageMetadata']
                token_info.update({
                    'input_tokens': usage.get('promptTokenCount', 0),
                    'output_tokens': usage.get('candidatesTokenCount', 0),
                    'total_tokens': usage.get('totalTokenCount', 0),
                    'token_source': 'gemini',
                    # Gemini Cache Detection - cachedContentTokenCount for implicit caching
                    'cached_content_token_count': usage.get('cachedContentTokenCount', 0)
                })
                
        except Exception as e:
            # If token extraction fails, just return defaults
            token_info['token_source'] = f'extraction_failed: {str(e)}'
            
        return token_info

    def _extract_valid_json(self, text: str) -> str:
        """Extract valid JSON from text that may contain extra content after the JSON.
        
        This method finds the first complete JSON object and ignores any trailing text.
        Handles cases where models add explanatory text after valid JSON.
        """
        try:
            # Find the start of JSON
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            # Count braces to find the end of the JSON object
            brace_count = 0
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the end of the JSON object
                        json_text = text[start_idx:i+1]
                        
                        # Test if it's valid JSON by parsing it
                        try:
                            json.loads(json_text)
                            return json_text
                        except json.JSONDecodeError:
                            # If parsing fails, continue looking
                            continue
            
            # If no valid JSON found, return None
            return None
            
        except Exception:
            return None

    def _parse_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response and extract structured data."""
        try:
            # FIRST: Extract token usage from raw response (before model parsing)
            token_usage = self._extract_token_usage(response_data)
            
            # THEN: Use the model's parse_response function if available
            model_module = self.model_config.get('module')
            if model_module and hasattr(model_module, 'parse_response'):
                # Model-specific parsing (handles OpenAI chat format, Gemini format, etc.)
                response_text = model_module.parse_response(response_data)
            else:
                # Fallback for Claude response format
                if 'content' in response_data and response_data['content']:
                    response_text = response_data['content'][0]['text']
                else:
                    response_text = str(response_data)
            
            # Extract JSON from cleaned response text using improved method
            json_text = self._extract_valid_json(response_text)
            if not json_text:
                return {'success': False, 'error': 'No valid JSON found in response'}
            
            parsed_data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['country', 'state', 'region', 'sector', 'exact_site']
            for field in required_fields:
                if field not in parsed_data:
                    parsed_data[field] = ''
            
            # Type conversion for numeric fields
            for coord_field in ['latitude', 'longitude', 'elevation_meters', 'coordinate_radius_meters']:
                if coord_field in parsed_data and parsed_data[coord_field] is not None:
                    try:
                        parsed_data[coord_field] = float(parsed_data[coord_field])
                    except (ValueError, TypeError):
                        parsed_data[coord_field] = None
            
            # Add token usage information (extracted at start of function)
            parsed_data.update(token_usage)
            
            parsed_data['success'] = True
            return parsed_data
            
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'JSON parsing failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Response parsing failed: {str(e)}'}
    
    def process_locality(self, locality: str, country: str, existing_lat: Optional[float] = None, 
                        existing_lon: Optional[float] = None, coord_source: str = "", 
                        coord_radius: Optional[float] = None) -> Dict[str, Any]:
        """Process a single locality using AI with caching support."""
        
        print(f"Processing: {locality[:50]}...")
        
        # Prepare coordinate context
        coordinate_context = self._prepare_coordinate_context(locality, existing_lat, existing_lon, coord_source, coord_radius)
        
        # Make API request
        api_response = self._make_api_request(locality, country, coordinate_context)
        
        if not api_response['success']:
            print(f"ERROR API failed: {api_response['error']}")
            return {
                'success': False,
                'error': api_response['error'],
                'country': country,
                'state': '',
                'region': '',
                'sector': '',
                'exact_site': locality,
                'latitude': existing_lat,
                'longitude': existing_lon,
                'coordinate_source': coord_source or 'failed',
                'coordinate_radius_meters': None,
                'elevation_meters': None,
                'elevation_original': '',
                'confidence': 'low',
                'collection_notes': '',
                'notes': f"AI processing failed: {api_response['error']}"
            }
        
        # Parse response
        parsed_result = self._parse_response(api_response['data'])
        
        if not parsed_result['success']:
            print(f"ERROR Parsing failed: {parsed_result['error']}")
            return {
                'success': False,
                'error': parsed_result['error'],
                'country': country,
                'state': '',
                'region': '',
                'sector': '',
                'exact_site': locality,
                'latitude': existing_lat,
                'longitude': existing_lon,
                'coordinate_source': coord_source or 'failed',
                'coordinate_radius_meters': None,
                'elevation_meters': None,
                'elevation_original': '',
                'confidence': 'low',
                'collection_notes': '',
                'notes': f"Response parsing failed: {parsed_result['error']}"
            }
        
        print(f"SUCCESS Success: {parsed_result.get('coordinate_source', 'processed')}")
        
        # Return successful result with token usage data
        return {
            'success': True,
            'country': parsed_result.get('country', country),
            'state': parsed_result.get('state', ''),
            'region': parsed_result.get('region', ''),
            'sector': parsed_result.get('sector', ''),
            'exact_site': parsed_result.get('exact_site', locality),
            'latitude': parsed_result.get('latitude'),
            'longitude': parsed_result.get('longitude'),
            'coordinate_source': parsed_result.get('coordinate_source', ''),
            'coordinate_radius_meters': parsed_result.get('coordinate_radius_meters'),
            'elevation_meters': parsed_result.get('elevation_meters'),
            'elevation_original': parsed_result.get('elevation_original', ''),
            'confidence': parsed_result.get('confidence', 'medium'),
            'collection_notes': parsed_result.get('collection_notes', ''),
            'notes': parsed_result.get('notes', ''),
            # Token usage data (including cache-specific tokens)
            'input_tokens': parsed_result.get('input_tokens', 0),
            'output_tokens': parsed_result.get('output_tokens', 0),
            'total_tokens': parsed_result.get('total_tokens', 0),
            'token_source': parsed_result.get('token_source', 'unknown'),
            'cache_creation_input_tokens': parsed_result.get('cache_creation_input_tokens', 0),
            'cache_read_input_tokens': parsed_result.get('cache_read_input_tokens', 0),
            # OpenAI cache tokens
            'cached_tokens': parsed_result.get('cached_tokens', 0),
            # Gemini cache tokens
            'cached_content_token_count': parsed_result.get('cached_content_token_count', 0)
        }