"""API client for communicating with the FastAPI backend."""

import os
import requests
from typing import Optional, Dict, List, Any
from datetime import date
import streamlit as st


class APIClient:
    """Client for making requests to the FastAPI backend."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client.

        Args:
            base_url: Base URL of the FastAPI backend (defaults to BACKEND_URL env var or localhost)
        """
        if base_url is None:
            base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.base_url = base_url
        self.session = requests.Session()

        # Add Cloudflare Access service token headers if configured
        cf_client_id = os.getenv("CF_ACCESS_CLIENT_ID")
        cf_client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")

        if cf_client_id and cf_client_secret:
            self.session.headers.update({
                "CF-Access-Client-Id": cf_client_id,
                "CF-Access-Client-Secret": cf_client_secret
            })
            print(f"[DEBUG] Cloudflare Access service token configured")
        else:
            print(f"[DEBUG] No Cloudflare Access service token configured")

        print(f"[DEBUG] APIClient initialized with base_url: {self.base_url}")

    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response and raise errors if needed."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", str(e))
            except:
                error_detail = str(e)
            raise Exception(f"API Error: {error_detail}")
        except ValueError as e:
            # JSON decode error
            raise Exception(f"Invalid JSON response: {str(e)}. Response text: {response.text[:200]}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection Error: {str(e)}")

    # Upload endpoints
    def preview_csv(self, file) -> Dict:
        """Preview CSV file before import."""
        files = {"file": file}
        response = self.session.post(f"{self.base_url}/api/upload/preview", files=files)
        return self._handle_response(response)

    def import_csv(self, import_request: Dict) -> Dict:
        """Import CSV with user actions."""
        response = self.session.post(
            f"{self.base_url}/api/upload/import",
            json=import_request
        )
        return self._handle_response(response)

    def get_ignore_list(self) -> List[Dict]:
        """Get list of ignored transaction descriptions."""
        response = self.session.get(f"{self.base_url}/api/upload/ignore-list")
        return self._handle_response(response)

    def add_to_ignore_list(self, description: str) -> Dict:
        """Add description to ignore list."""
        response = self.session.post(
            f"{self.base_url}/api/upload/ignore-list",
            params={"description": description}
        )
        return self._handle_response(response)

    def remove_from_ignore_list(self, ignore_id: int) -> Dict:
        """Remove description from ignore list."""
        response = self.session.delete(
            f"{self.base_url}/api/upload/ignore-list/{ignore_id}"
        )
        return self._handle_response(response)

    # Transaction endpoints
    def create_transaction(self, transaction_data: Dict) -> Dict:
        """Create a new transaction manually."""
        response = self.session.post(
            f"{self.base_url}/api/transactions",
            json=transaction_data
        )
        return self._handle_response(response)

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """Get list of transactions with filters."""
        params = {
            "limit": limit,
            "offset": offset
        }
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if category:
            params["category"] = category
        if search:
            params["search"] = search

        response = self.session.get(f"{self.base_url}/api/transactions", params=params)
        return self._handle_response(response)

    def get_transaction(self, transaction_id: int) -> Dict:
        """Get single transaction by ID."""
        response = self.session.get(f"{self.base_url}/api/transactions/{transaction_id}")
        return self._handle_response(response)

    def update_transaction(self, transaction_id: int, update_data: Dict) -> Dict:
        """Update transaction."""
        response = self.session.patch(
            f"{self.base_url}/api/transactions/{transaction_id}",
            json=update_data
        )
        return self._handle_response(response)

    def delete_transaction(self, transaction_id: int) -> Dict:
        """Delete transaction."""
        response = self.session.delete(f"{self.base_url}/api/transactions/{transaction_id}")
        return self._handle_response(response)

    # Subscription endpoints
    def create_subscription(self, subscription_data: Dict) -> Dict:
        """Create new subscription."""
        response = self.session.post(
            f"{self.base_url}/api/subscriptions",
            json=subscription_data
        )
        return self._handle_response(response)

    def get_subscriptions(self, active_only: bool = False) -> Dict:
        """Get list of subscriptions."""
        params = {"active_only": active_only}
        response = self.session.get(f"{self.base_url}/api/subscriptions", params=params)
        return self._handle_response(response)

    def get_subscription(self, subscription_id: int) -> Dict:
        """Get single subscription by ID."""
        response = self.session.get(f"{self.base_url}/api/subscriptions/{subscription_id}")
        return self._handle_response(response)

    def update_subscription(self, subscription_id: int, update_data: Dict) -> Dict:
        """Update subscription."""
        response = self.session.patch(
            f"{self.base_url}/api/subscriptions/{subscription_id}",
            json=update_data
        )
        return self._handle_response(response)

    def delete_subscription(self, subscription_id: int) -> Dict:
        """Delete subscription."""
        response = self.session.delete(f"{self.base_url}/api/subscriptions/{subscription_id}")
        return self._handle_response(response)

    def link_transaction_to_subscription(self, transaction_id: int, subscription_id: int) -> Dict:
        """Link transaction to subscription."""
        response = self.session.post(
            f"{self.base_url}/api/subscriptions/link",
            json={"transaction_id": transaction_id, "subscription_id": subscription_id}
        )
        return self._handle_response(response)

    def unlink_transaction(self, transaction_id: int) -> Dict:
        """Unlink transaction from subscription."""
        response = self.session.delete(f"{self.base_url}/api/subscriptions/link/{transaction_id}")
        return self._handle_response(response)

    # Income source endpoints
    def create_income_source(self, income_source_data: Dict) -> Dict:
        """Create new income source."""
        response = self.session.post(
            f"{self.base_url}/api/income-sources",
            json=income_source_data
        )
        return self._handle_response(response)

    def get_income_sources(self, active_only: bool = False) -> Dict:
        """Get list of income sources."""
        params = {"active_only": active_only}
        response = self.session.get(f"{self.base_url}/api/income-sources", params=params)
        return self._handle_response(response)

    def get_income_source(self, income_source_id: int) -> Dict:
        """Get single income source by ID."""
        response = self.session.get(f"{self.base_url}/api/income-sources/{income_source_id}")
        return self._handle_response(response)

    def update_income_source(self, income_source_id: int, update_data: Dict) -> Dict:
        """Update income source metadata."""
        response = self.session.patch(
            f"{self.base_url}/api/income-sources/{income_source_id}",
            json=update_data
        )
        return self._handle_response(response)

    def update_expected_amount(self, income_source_id: int, expected_amount: float, note: Optional[str] = None) -> Dict:
        """Update expected amount for an income source."""
        response = self.session.patch(
            f"{self.base_url}/api/income-sources/{income_source_id}/expected-amount",
            json={"expected_amount": expected_amount, "note": note}
        )
        return self._handle_response(response)

    def delete_income_source(self, income_source_id: int) -> Dict:
        """Delete income source."""
        response = self.session.delete(f"{self.base_url}/api/income-sources/{income_source_id}")
        return self._handle_response(response)

    def link_transaction_to_income_source(self, transaction_id: int, income_source_id: int) -> Dict:
        """Link transaction to income source."""
        response = self.session.post(
            f"{self.base_url}/api/income-sources/link",
            json={"transaction_id": transaction_id, "income_source_id": income_source_id}
        )
        return self._handle_response(response)

    def unlink_transaction_from_income_source(self, transaction_id: int) -> Dict:
        """Unlink transaction from income source."""
        response = self.session.delete(f"{self.base_url}/api/income-sources/link/{transaction_id}")
        return self._handle_response(response)

    def get_income_source_history(self, income_source_id: int) -> Dict:
        """Get historical expected amount changes for an income source."""
        response = self.session.get(f"{self.base_url}/api/income-sources/{income_source_id}/history")
        return self._handle_response(response)

    # Report endpoints
    def get_transactions_by_category(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> Dict:
        """Get transactions grouped by category."""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if category:
            params["category"] = category
        if transaction_type:
            params["transaction_type"] = transaction_type

        response = self.session.get(f"{self.base_url}/api/reports/by-category", params=params)
        return self._handle_response(response)

    def get_transactions_by_month(self, year: int) -> Dict:
        """Get transactions grouped by month."""
        response = self.session.get(
            f"{self.base_url}/api/reports/by-month",
            params={"year": year}
        )
        return self._handle_response(response)

    def get_biggest_transactions(
        self,
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> Dict:
        """Get biggest transactions."""
        params = {"limit": limit}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if category:
            params["category"] = category
        if transaction_type:
            params["transaction_type"] = transaction_type

        response = self.session.get(f"{self.base_url}/api/reports/biggest-transactions", params=params)
        return self._handle_response(response)

    def get_biggest_by_category(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None
    ) -> Dict:
        """Get biggest transaction per category."""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if category:
            params["category"] = category

        response = self.session.get(f"{self.base_url}/api/reports/biggest-by-category", params=params)
        return self._handle_response(response)

    def get_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> Dict:
        """Get transaction statistics."""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if category:
            params["category"] = category
        if transaction_type:
            params["transaction_type"] = transaction_type

        response = self.session.get(f"{self.base_url}/api/reports/statistics", params=params)
        return self._handle_response(response)

    def get_monthly_comparison(self, year: int, category: Optional[str] = None) -> Dict:
        """Get monthly comparison."""
        params = {"year": year}
        if category:
            params["category"] = category

        response = self.session.get(f"{self.base_url}/api/reports/monthly-comparison", params=params)
        return self._handle_response(response)

    def get_subscription_summary(self) -> List[Dict]:
        """Get subscription summary with statistics."""
        response = self.session.get(f"{self.base_url}/api/reports/subscriptions")
        return self._handle_response(response)

    def get_expected_income_summary(self, year: int, month: int) -> Dict:
        """Get expected income summary for dashboard."""
        params = {"year": year, "month": month}
        response = self.session.get(f"{self.base_url}/api/reports/expected-income", params=params)
        return self._handle_response(response)

    # Category endpoints
    def get_all_categories(self) -> List[Dict]:
        """Get all categories."""
        response = self.session.get(f"{self.base_url}/api/categories")
        return self._handle_response(response)

    def get_category(self, category_id: int) -> Dict:
        """Get single category by ID."""
        response = self.session.get(f"{self.base_url}/api/categories/{category_id}")
        return self._handle_response(response)

    def update_category(self, category_id: int, update_data: Dict) -> Dict:
        """Update category name."""
        response = self.session.patch(
            f"{self.base_url}/api/categories/{category_id}",
            json=update_data
        )
        return self._handle_response(response)

    # Database export/import endpoints
    def export_database(self) -> Dict:
        """Export entire database to JSON format."""
        response = self.session.post(f"{self.base_url}/api/database/export")
        return self._handle_response(response)

    def preview_database_import(self, data: Dict) -> Dict:
        """Preview database import to see conflicts."""
        response = self.session.post(
            f"{self.base_url}/api/database/import/preview",
            json=data
        )
        return self._handle_response(response)

    def execute_database_import(self, data: Dict, create_backup: bool = True) -> Dict:
        """Execute database import with skip duplicates strategy."""
        request = {
            "data": data,
            "create_backup": create_backup
        }
        response = self.session.post(
            f"{self.base_url}/api/database/import/execute",
            json=request
        )
        return self._handle_response(response)

    def create_backup(self) -> Dict:
        """Create a manual database backup."""
        response = self.session.post(f"{self.base_url}/api/database/backup/create")
        return self._handle_response(response)

    def list_backups(self) -> List[Dict]:
        """List all available database backups."""
        response = self.session.get(f"{self.base_url}/api/database/backup/list")
        return self._handle_response(response)

    def restore_backup(self, backup_file: str) -> Dict:
        """Restore database from a backup file."""
        response = self.session.post(
            f"{self.base_url}/api/database/backup/restore",
            json={"backup_file": backup_file}
        )
        return self._handle_response(response)

    def health_check(self) -> Dict:
        """Check API health."""
        url = f"{self.base_url}/health"
        print(f"[DEBUG] Calling health check: {url}")
        response = self.session.get(url)
        print(f"[DEBUG] Health check response status: {response.status_code}")
        print(f"[DEBUG] Health check response headers: {dict(response.headers)}")
        print(f"[DEBUG] Health check response text (first 200 chars): {response.text[:200]}")
        return self._handle_response(response)


# Singleton instance
@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance."""
    return APIClient()
