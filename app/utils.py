import pandas as pd
from datetime import datetime
from app.models import db, Advertiser, SpendingData

def process_csv_upload(file_path):
    """Process uploaded CSV file and import advertiser spending data."""
    try:
        # Try different encodings to read the CSV file
        encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                # Try different separators
                separators = ['\t', ',', ';']
                for sep in separators:
                    try:
                        df = pd.read_csv(file_path, sep=sep, encoding=encoding)
                        if df.shape[1] > 1:  # Make sure we have multiple columns
                            break
                    except:
                        continue
                if df is not None and df.shape[1] > 1:
                    break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                continue
        
        if df is None:
            return False, "Could not read CSV file with any supported encoding"
        
        # Create a case-insensitive column mapping
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'a_adver_e' in col_lower or 'adver' in col_lower:
                column_mapping[col] = 'advertiser_name'
            elif 'year' in col_lower:
                column_mapping[col] = 'year'
            elif 'cinema' in col_lower:
                column_mapping[col] = 'cinema'
            elif 'fillboard' in col_lower or 'billboard' in col_lower:
                column_mapping[col] = 'billboard'
            elif 'indoor' in col_lower:
                column_mapping[col] = 'indoor_tv'
            elif 'internet' in col_lower:
                column_mapping[col] = 'internet'
            elif 'magazine' in col_lower:
                column_mapping[col] = 'magazines'
            elif 'newspaper' in col_lower:
                column_mapping[col] = 'newspapers'
            elif 'outdoor' in col_lower and 'static' in col_lower:
                column_mapping[col] = 'outdoor_static'
            elif 'radio' in col_lower:
                column_mapping[col] = 'radio'
            elif col_lower == 'tv':
                column_mapping[col] = 'tv'
            elif 'grand' in col_lower and 'total' in col_lower:
                column_mapping[col] = 'grand_total'
                
        df.rename(columns=column_mapping, inplace=True)
        
        # Check which columns are available and fill NaN values with 0
        all_numeric_columns = ['cinema', 'billboard', 'indoor_tv', 'internet', 'magazines', 
                              'newspapers', 'outdoor_static', 'radio', 'tv', 'grand_total']
        
        # Only process columns that exist in the DataFrame
        numeric_columns = [col for col in all_numeric_columns if col in df.columns]
        missing_columns = [col for col in all_numeric_columns if col not in df.columns]
        
        if missing_columns:
            # Add missing columns with default value 0
            for col in missing_columns:
                df[col] = 0
        
        # Now we can safely fill NaN values
        df[all_numeric_columns] = df[all_numeric_columns].fillna(0)
        
        # Clean and convert numeric values
        for col in all_numeric_columns:
            # Convert to string first
            df[col] = df[col].astype(str)
            
            # Simple cleaning for this specific CSV format
            # Numbers use spaces as thousands separators (e.g., "14 722")
            def clean_number(value):
                if pd.isna(value) or value in ['', 'nan', '0.0', 'None']:
                    return 0.0
                
                value = str(value).strip()
                
                # Handle empty or null values
                if not value or value in ['nan', '', '0.0', 'None']:
                    return 0.0
                
                # Remove spaces (thousands separators)
                value = value.replace(' ', '')
                
                # Remove any Unicode characters that might appear
                import re
                value = re.sub(r'[^\d.,]', '', value)
                
                # If empty after cleaning, return 0
                if not value:
                    return 0.0
                
                # Convert to float
                try:
                    return float(value)
                except ValueError:
                    return 0.0
            
            df[col] = df[col].apply(clean_number)
        
        # Get unique advertisers from the import
        unique_advertisers = df['advertiser_name'].unique()
        
        # Option 1: Delete all spending data for advertisers in the import
        # This ensures clean overwrite of their data
        for advertiser_name in unique_advertisers:
            advertiser = Advertiser.query.filter_by(name=advertiser_name).first()
            if advertiser:
                # Delete existing spending data for this advertiser
                SpendingData.query.filter_by(advertiser_id=advertiser.id).delete()
        
        db.session.flush()  # Ensure deletions are processed
        
        # Process each row - now all will be new imports
        imported_count = 0
        
        # Define our agencies
        our_agencies = [
            'BPN (US) - IPG',
            'Initiate (Open agency) IPG',
            'Media brands digital - IPG',
            'UM (Inspired) IPG'
        ]
        
        # Define public sector keywords for non-market detection
        public_sector_keywords = [
            'ministerija', 'ministeri', 'ministry',
            'savivaldyb', 'municipality',
            'departament', 'department',
            'tarnyba', 'taryba', 'service', 'council',
            'agentūra', 'agency',
            'fondas', 'fund',
            'centras', 'center', 'centre',
            'inspekcija', 'inspection',
            'direkcija', 'directorate',
            'komisija', 'commission',
            'valstybinė', 'valstybinis', 'state',
            'nacionalinis', 'national',
            'lietuvos respublikos', 'republic of lithuania',
            'vyriausybė', 'government',
            'seimas', 'parliament'
        ]
        
        for _, row in df.iterrows():
            # Get or create advertiser
            advertiser = Advertiser.query.filter_by(name=row['advertiser_name']).first()
            if not advertiser:
                advertiser = Advertiser(name=row['advertiser_name'])
                
                # Set initial lead status to non_qualified
                advertiser.lead_status = 'non_qualified'
                
                db.session.add(advertiser)
                db.session.flush()  # Get the ID without committing
            
            # Create new spending data (all are new since we deleted existing)
            spending_data = SpendingData(
                advertiser_id=advertiser.id,
                year=int(row['year']),
                cinema=row['cinema'],
                billboard=row['billboard'],
                indoor_tv=row['indoor_tv'],
                internet=row['internet'],
                magazines=row['magazines'],
                newspapers=row['newspapers'],
                outdoor_static=row['outdoor_static'],
                radio=row['radio'],
                tv=row['tv'],
                grand_total=row['grand_total']
            )
            db.session.add(spending_data)
            imported_count += 1
        
        db.session.commit()
        
        # Update lead statuses based on agencies
        statuses_updated = update_lead_statuses_by_agency()
        
        return True, f"Successfully imported {imported_count} spending records for {len(unique_advertisers)} advertisers. Previous spending data has been overwritten. Updated {statuses_updated} lead statuses based on agency assignments."
    
    except Exception as e:
        db.session.rollback()
        return False, f"Error processing CSV: {str(e)}"

def get_lead_status_color(status):
    """Return color class for lead status."""
    colors = {
        'non_qualified': 'secondary',
        'ours': 'success',
        'cold': 'primary',
        'warm': 'warning',
        'hot': 'danger',
        'lost': 'dark',
        'non_market': 'light'
    }
    return colors.get(status, 'secondary')

def format_currency(value):
    """Format number as currency."""
    if value is None:
        return "€0"
    return f"€{value:,.0f}"

def update_lead_statuses_by_agency():
    """Update lead statuses based on current agency assignments."""
    from app.models import Advertiser
    
    # Define our agencies
    our_agencies = [
        'BPN (US) - IPG',
        'Initiate (Open agency) IPG',
        'Media brands digital - IPG',
        'UM (Inspired) IPG'
    ]
    
    # Define public sector keywords for non-market detection
    public_sector_keywords = [
        'ministerija', 'ministeri', 'ministry',
        'savivaldyb', 'municipality',
        'departament', 'department',
        'tarnyba', 'taryba', 'service', 'council',
        'agentūra', 'agency',
        'fondas', 'fund',
        'centras', 'center', 'centre',
        'inspekcija', 'inspection',
        'direkcija', 'directorate',
        'komisija', 'commission',
        'valstybinė', 'valstybinis', 'state',
        'nacionalinis', 'national',
        'lietuvos respublikos', 'republic of lithuania',
        'vyriausybė', 'government',
        'seimas', 'parliament'
    ]
    
    # Update advertisers with our agencies to 'ours' status
    advertisers_updated = 0
    
    # Set 'ours' status for our agencies
    for agency in our_agencies:
        count = Advertiser.query.filter_by(
            current_agency=agency,
            lead_status='non_qualified'
        ).update({'lead_status': 'ours'})
        advertisers_updated += count
    
    # Set 'non_market' status for public sector
    all_advertisers = Advertiser.query.filter_by(lead_status='non_qualified').all()
    for advertiser in all_advertisers:
        name_lower = advertiser.name.lower()
        if any(keyword in name_lower for keyword in public_sector_keywords):
            advertiser.lead_status = 'non_market'
            advertisers_updated += 1
    
    db.session.commit()
    return advertisers_updated