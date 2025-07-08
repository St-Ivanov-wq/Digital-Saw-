"""
Google Sheets export logic for the sheet cutting app.
"""

import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Optional
from models.part import Sheet

GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID', None)

class GoogleSheetsExporter:
    def __init__(self, service_account_file: str):
        self.service_account_file = service_account_file
        self.credentials = None
        self.service = None

    def authenticate(self) -> bool:
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=self.credentials)
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def export_cutting_plan(self, sheets: List[Sheet], filename: Optional[str] = None):
        if not self.authenticate():
            return False
        try:
            spreadsheet_id = GOOGLE_SHEET_ID
            if not spreadsheet_id:
                if filename is None:
                    filename = "Cutting_Plan_Master"
                spreadsheet = {
                    'properties': {
                        'title': filename
                    }
                }
                spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
                spreadsheet_id = spreadsheet['spreadsheetId']
                print(f"Created new Google Sheet. Set GOOGLE_SHEET_ID to: {spreadsheet_id}")
                # Grant edit permission to a user (email hidden for privacy)
                try:
                    drive_service = build('drive', 'v3', credentials=self.credentials)
                    permission = {
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': os.environ.get('EXPORT_SHARE_EMAIL')  # Set this in your environment
                    }
                    if permission['emailAddress']:
                        drive_service.permissions().create(
                            fileId=spreadsheet_id,
                            body=permission,
                            fields='id',
                            sendNotificationEmail=False
                        ).execute()
                        print("Granted edit permission to the configured email.")
                    else:
                        print("No export share email configured. Skipping permission grant.")
                except Exception:
                    print("Failed to grant permission (details hidden for privacy).")
            current_date = time.strftime("%Y-%m-%d_%H-%M-%S")
            add_sheet_request = {
                'requests': [
                    {
                        'addSheet': {
                            'properties': {
                                'title': current_date
                            }
                        }
                    }
                ]
            }
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=add_sheet_request
            ).execute()
            new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            sheet_details = []
            for i, sheet in enumerate(sheets, 1):
                sheet_details.append([
                    f"Sheet {i}",
                    f"{sheet.size[0]}x{sheet.size[1]}",
                    sheet.material,
                    str(sheet.thickness),
                    f"{sheet.utilization*100:.2f}%",
                    f"{sheet.efficiency['waste_percent']*100:.2f}%",
                    str(len(sheet.placements)),
                    sheet.algorithm
                ])
            placement_details = []
            for sheet_index, sheet in enumerate(sheets, 1):
                for placement in sheet.placements:
                    placement_details.append([
                        f"Sheet {sheet_index}",
                        placement.ref,
                        str(placement.width),
                        str(placement.height),
                        "Rotated" if placement.rotated else "Normal",
                        str(placement.x),
                        str(placement.y),
                        sheet.material,
                        str(sheet.thickness)
                    ])
            sheet_body = {
                'values': [
                    ["Sheet #", "Dimensions (mm)", "Material", "Thickness (mm)",
                     "Utilization", "Waste %", "Part Count", "Algorithm"],
                    *sheet_details
                ]
            }
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{current_date}'!A1",
                valueInputOption="RAW",
                body=sheet_body
            ).execute()
            placement_body = {
                'values': [
                    ["Sheet #", "Part Ref", "Width (mm)", "Height (mm)", "Orientation",
                     "X Position", "Y Position", "Material", "Thickness (mm)"],
                    *placement_details
                ]
            }
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{current_date}'!A{len(sheet_details) + 3}",
                valueInputOption="RAW",
                body=placement_body
            ).execute()
            header_format = {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            }
            format_request = {
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": new_sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1
                            },
                            "cell": {"userEnteredFormat": header_format},
                            "fields": "userEnteredFormat"
                        }
                    },
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": new_sheet_id,
                                "startRowIndex": len(sheet_details) + 2,
                                "endRowIndex": len(sheet_details) + 3
                            },
                            "cell": {"userEnteredFormat": header_format},
                            "fields": "userEnteredFormat"
                        }
                    },
                    {
                        "autoResizeDimensions": {
                            "dimensions": {
                                "dimension": "COLUMNS",
                                "sheetId": new_sheet_id
                            }
                        }
                    }
                ]
            }
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=format_request
            ).execute()
            print(f"Google Sheets export complete. Link: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            return spreadsheet_id
        except Exception as e:
            print(f"Export failed: {e}")
            return False
