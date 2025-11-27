"""
Database management module for LinkedIn job scraper.
Handles SQLite database operations including initialization and CRUD operations.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Set
from contextlib import contextmanager


class JobDatabase:
    """Manages SQLite database operations for job tracking."""
    
    def __init__(self, db_path: str = "jobs.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def initialize_database(self):
        """Create jobs table if it doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    link TEXT,
                    date_posted TEXT,
                    last_seen TEXT,
                    status TEXT DEFAULT 'not_applied',
                    applied_on TEXT,
                    expired INTEGER DEFAULT 0
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON jobs(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expired 
                ON jobs(expired)
            """)
    
    def insert_job(self, job_data: Dict) -> bool:
        """
        Insert a new job into the database.
        
        Args:
            job_data: Dictionary containing job information
            
        Returns:
            True if inserted, False if job already exists
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            try:
                cursor.execute("""
                    INSERT INTO jobs (
                        job_id, title, company, location, 
                        link, date_posted, last_seen, status, expired
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_data['job_id'],
                    job_data['title'],
                    job_data['company'],
                    job_data['location'],
                    job_data['link'],
                    job_data.get('date_posted', ''),
                    today,
                    'not_applied',
                    0
                ))
                return True
            except sqlite3.IntegrityError:
                # Job already exists
                return False
    
    def update_last_seen(self, job_id: str) -> bool:
        """
        Update the last_seen date for an existing job and mark as not expired.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if updated, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute("""
                UPDATE jobs 
                SET last_seen = ?, expired = 0
                WHERE job_id = ?
            """, (today, job_id))
            
            return cursor.rowcount > 0
    
    def get_all_active_job_ids(self) -> Set[str]:
        """
        Get all job IDs that are not marked as expired.
        
        Returns:
            Set of active job IDs
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_id FROM jobs WHERE expired = 0
            """)
            return {row['job_id'] for row in cursor.fetchall()}
    
    def mark_jobs_as_expired(self, job_ids: List[str]) -> int:
        """
        Mark multiple jobs as expired.
        
        Args:
            job_ids: List of job IDs to mark as expired
            
        Returns:
            Number of jobs marked as expired
        """
        if not job_ids:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(job_ids))
            cursor.execute(f"""
                UPDATE jobs 
                SET expired = 1
                WHERE job_id IN ({placeholders})
            """, job_ids)
            
            return cursor.rowcount
    
    def get_job_stats(self) -> Dict:
        """
        Get statistics about jobs in the database.
        
        Returns:
            Dictionary with job statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM jobs")
            total = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as active FROM jobs WHERE expired = 0")
            active = cursor.fetchone()['active']
            
            cursor.execute("SELECT COUNT(*) as expired FROM jobs WHERE expired = 1")
            expired = cursor.fetchone()['expired']
            
            cursor.execute("""
                SELECT COUNT(*) as applied 
                FROM jobs WHERE status = 'applied'
            """)
            applied = cursor.fetchone()['applied']
            
            return {
                'total': total,
                'active': active,
                'expired': expired,
                'applied': applied,
                'not_applied': active - applied
            }
    
    def export_jobs_to_dict(self, active_only: bool = True) -> List[Dict]:
        """
        Export jobs to a list of dictionaries.
        
        Args:
            active_only: If True, only export non-expired jobs
            
        Returns:
            List of job dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute("""
                    SELECT * FROM jobs WHERE expired = 0
                    ORDER BY last_seen DESC
                """)
            else:
                cursor.execute("""
                    SELECT * FROM jobs
                    ORDER BY last_seen DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
