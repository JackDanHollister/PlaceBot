# PlaceBot Example Datasets

This directory contains sample locality datasets for testing and demonstrating PlaceBot's capabilities.

## Dataset Overview

### 🌱 Botanical Garden Localities
**sample_localities.tsv** (10 records)
- Quick demonstration dataset
- Major botanical gardens worldwide
- Perfect for first-time users
- Format: TSV with locality_id and locality_description columns

### 🐝 Bombus (Bumblebee) Collections
**bombus_100.csv** (100 records)
- Real museum specimen data
- Bumblebee collection localities from natural history collections
- Diverse geographic locations
- Tests model performance on scientific specimen data

**bombus_test.tsv** (smaller test set)
- Subset for quick testing
- Bumblebee specimen localities

### 🦟 Odonata (Dragonfly) Collections
**odonata_100.csv** (100 records)
- Real museum specimen data
- Dragonfly and damselfly collection localities
- Complex locality descriptions
- Tests parsing of detailed specimen data

**odonata_localities.tsv** (full dataset)
- Complete odonata collection dataset
- Extensive variety of locality formats

### 🌍 Botanical Gardens Edinburgh (BGE)
**BGE_1_test100.csv** / **BGE_1_test100.tsv** (100 records)
- Royal Botanic Garden Edinburgh specimen data
- High-quality curated localities
- International collection coverage
- Excellent for accuracy testing

**BGE_1_test20.tsv** (20 records)
- Quick test subset
- Rapid validation of model performance

### 🧪 Test Datasets
**test_small.tsv** (minimal test set)
- Tiny dataset for rapid testing
- Quick validation of installation
- Fast model response verification

**ai_test.tsv** (AI testing suite)
- Specifically designed for AI model testing
- Edge cases and challenging localities
- Model performance evaluation

## Usage Examples

### Quick Start
```bash
# Run PlaceBot on the sample dataset
placebot

# When prompted, select:
# - Processing mode: real-time
# - Model: Claude 3.5 Haiku (fast and reliable)
# - Input file: examples/sample_localities.tsv
```

### Testing Model Performance
```bash
# Test on 100 real specimens
placebot
# Select: bombus_100.csv or odonata_100.csv
```

### Batch Processing
```bash
# For larger datasets like BGE_1_test100
placebot-batch
# Select: BGE_1_test100.tsv
```

## Data Format

All datasets follow this structure:

```tsv
locality_id	locality_description
1	"California, San Francisco Bay, Golden Gate Park"
2	"UK, Scotland, Edinburgh, Royal Botanic Garden"
```

- **locality_id**: Unique identifier for each record
- **locality_description**: Natural language locality text

## Expected Results

PlaceBot will extract:
- **Latitude**: Decimal degrees
- **Longitude**: Decimal degrees
- **Confidence**: Model confidence in extraction
- **Processing time**: Time taken per record
- **Success rate**: Percentage of successful extractions

Typical accuracy:
- **Cloud models**: 100% success rate
- **Local models**: 97-100% success rate

## Dataset Sources

- **Botanical gardens**: Curated list of major institutions
- **Museum specimens**: Real biodiversity collection data
- **BGE data**: Royal Botanic Garden Edinburgh collections
- **Test data**: Custom-designed validation sets

## Adding Your Own Data

To test PlaceBot with your own localities:

1. Create a TSV or CSV file with these columns:
   - `locality_id`: Unique ID
   - `locality_description`: Locality text

2. Save in this examples directory or any location

3. Run PlaceBot and select your file

## Performance Benchmarks

Based on testing with these datasets:

| Dataset | Records | Avg Time/Record | Success Rate |
|---------|---------|-----------------|--------------|
| sample_localities | 10 | 7.2s | 100% |
| bombus_100 | 100 | 7.5s | 100% |
| odonata_100 | 100 | 7.3s | 100% |
| BGE_1_test100 | 100 | 7.1s | 100% |

*Benchmarks using Claude 3.5 Haiku model*

## Need Help?

See the main [README.md](../README.md) for:
- Installation instructions
- Model selection guide
- Cost optimization tips
- Troubleshooting

---

**Happy geocoding! 🗺️**
