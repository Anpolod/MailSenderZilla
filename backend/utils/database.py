"""Database utility functions for reading from Main_DataBase.db."""
import sqlite3
import pandas as pd
import logging
from typing import List, Dict, Any
from backend.models.database import DB_PATH

logger = logging.getLogger(__name__)


def get_all_tables() -> List[str]:
    """Get list of all tables in the database, excluding system tables."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all tables (excluding SQLite system tables)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        raise Exception(f"Failed to get tables: {e}")


def get_table_columns(table_name: str) -> List[str]:
    """Get list of columns in a table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Escape table name for SQLite
        table_name_escaped = f'"{table_name}"'
        cursor.execute(f"PRAGMA table_info({table_name_escaped})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        raise Exception(f"Failed to get columns from table {table_name}: {e}")


def detect_email_column(table_name: str, columns: List[str] = None) -> str:
    """Auto-detect email column name from table."""
    if columns is None:
        columns = get_table_columns(table_name)
    
    # Common email column name variants
    email_variants = ['Email', 'email', 'E-Mail', 'E-mail', 'e-mail', 'EMAIL', 'e_mail', 'E_MAIL', 'mail', 'Mail']
    
    for variant in email_variants:
        if variant in columns:
            return variant
    
    return None


def preview_table_emails(table_name: str, email_column: str = None, limit: int = 10) -> Dict[str, Any]:
    """Preview emails from a table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Get columns if not provided
        columns = get_table_columns(table_name)
        
        # Auto-detect email column if not provided
        if email_column is None:
            email_column = detect_email_column(table_name, columns)
            if email_column is None:
                return {
                    'error': f"No email column found. Available columns: {', '.join(columns)}"
                }
        
        # Escape table and column names
        table_name_escaped = f'"{table_name}"'
        email_col_escaped = f'"{email_column}"'
        
        # Count total rows with emails
        count_query = f'SELECT COUNT(*) FROM {table_name_escaped} WHERE {email_col_escaped} IS NOT NULL AND {email_col_escaped} != ""'
        cursor = conn.cursor()
        cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        # Get preview
        preview_query = f'SELECT {email_col_escaped} FROM {table_name_escaped} WHERE {email_col_escaped} IS NOT NULL AND {email_col_escaped} != "" LIMIT {limit}'
        df = pd.read_sql_query(preview_query, conn)
        
        conn.close()
        
        return {
            'table_name': table_name,
            'email_column': email_column,
            'total_count': total_count,
            'preview': df[email_column].tolist() if email_column in df.columns else []
        }
    except Exception as e:
        return {'error': str(e)}


def read_emails_from_table(table_name: str, email_column: str = None) -> pd.DataFrame:
    """Read emails from SQLite database table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Get columns
        columns = get_table_columns(table_name)
        
        # Auto-detect email column if not provided
        if email_column is None:
            email_column = detect_email_column(table_name, columns)
            if email_column is None:
                raise ValueError(
                    f"Column 'email' not found in table '{table_name}'. "
                    f"Available columns: {', '.join(columns)}"
                )
        
        # Escape table and column names
        table_name_escaped = f'"{table_name}"'
        email_col_escaped = f'"{email_column}"'
        
        # Read data
        query = f'SELECT *, ROWID as _rowid FROM {table_name_escaped} WHERE {email_col_escaped} IS NOT NULL AND {email_col_escaped} != ""'
        df = pd.read_sql_query(query, conn)
        
        # Rename email column to standard "Email" if needed
        if email_column != "Email" and email_column in df.columns:
            df["Email"] = df[email_column]
        
        conn.close()
        return df
    except Exception as e:
        raise Exception(f"Failed to read emails from table {table_name}: {e}")


def read_emails_from_tables(table_names: List[str], email_column: str = None) -> pd.DataFrame:
    """Read emails from multiple SQLite database tables and combine them."""
    all_dfs = []
    
    for table_name in table_names:
        try:
            df = read_emails_from_table(table_name, email_column)
            if not df.empty:
                # Add source table column for tracking
                df['_source_table'] = table_name
                all_dfs.append(df)
        except Exception as e:
            # Log error but continue with other tables
            logger.warning(f"Failed to read from table {table_name}: {e}")
            continue
    
    if not all_dfs:
        return pd.DataFrame()
    
    # Combine all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Remove duplicates based on email
    email_col = 'Email' if 'Email' in combined_df.columns else email_column
    if email_col and email_col in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=[email_col], keep='first')
    
    return combined_df
