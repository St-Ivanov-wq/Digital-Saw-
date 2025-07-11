"""
Google Sheets export logic for the sheet cutting app.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Optional
from models.part import Sheet
import time
import os

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
            if filename is None:
                filename = "Cutting_Plan_" + time.strftime("%d-%m-%Y")
            spreadsheet = {
                'properties': {
                    'title': filename
                }
            }
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = spreadsheet['spreadsheetId']
            first_sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
            current_date = time.strftime("%d-%m-%Y")
            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": first_sheet_id,
                            "title": current_date
                        },
                        "fields": "title"
                    }
                }
            ]
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
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
                    ["Лист#", "Dimensions (mm)", "Материал", "Дебелина (mm)", 
                     "Ефективност", "Отпадък %", "Брой части", "Алгоритъм"],
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
                    ["Лист #", "Part Ref", "Широчина (mm)", "Височина (mm)", "Ориентация", 
                     "X Position", "Y Position", "Материал", "Дебелина (mm)"],
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
                                "sheetId": first_sheet_id,
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
                                "sheetId": first_sheet_id,
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
                                "sheetId": first_sheet_id
                            }
                        }
                    }
                ]
            }
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=format_request
            ).execute()
            try:
                drive_service = build('drive', 'v3', credentials=self.credentials)
                permission = {
                    'type': 'anyone',
                    'role': 'writer',
                }
                drive_service.permissions().create(
                    fileId=spreadsheet_id,
                    body=permission,
                    fields='id',
                ).execute()
            except Exception as e:
                print(f"Failed to set public permission: {e}")
            return spreadsheet_id
        except Exception as e:
            print(f"Export failed: {e}")
            return False
