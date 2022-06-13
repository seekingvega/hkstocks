import os, sys, json, datetime
from fastapi import FastAPI, File, UploadFile, Request, Response, HTTPException
from typing import List, Tuple, Union
from pydantic import BaseModel

app_version = 0.01
b_add_app_name = os.getenv("ADD_APP_NAME", 'False').lower() in ['true', '1', 't']
app_name = '/hkstocks' if b_add_app_name else '' # This is for applications routing with $uri in ngnix config
app = FastAPI(
	title = 'HKStocks API',
	description = "free API to get Hong Kong List Stocks data",
	version = app_version,
	docs_url = f'{app_name}/docs', redoc_url = None,
	openapi_url = f'{app_name}/openapi.json'
)

class ConstituentResult(BaseModel):
	index: str
	name: str
	constituents: List[dict]

class LotSizeResult(BaseModel):
	ticker: str
	lot_size: int

class DivResult(BaseModel):
	ticker: str
	dividends: List[dict]

from hkex_utils import parse_hk_ticker, get_lot_size, scrap_hk_stock_div, \
					get_hangseng_constituent_df
HSI_DICT = {
	'HCS': {'name': 'Hang Seng Compositie SmallCap Index',
			'xls_url': 'https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/other_materials/HSSI_LISTe.xls'
			}
}

@app.get(app_name +"/{index}/constituents",
	response_model = ConstituentResult, response_model_exclude_unset = True)
async def get_hsi_constituents(index: str = 'HCS'):
	'''get Hang Seng Index Constituents

	* `index`: Hang Seng Index Symbol, currently only support HCS (please add [an issue](https://github.com/seekingvega/hkstocks/issues) for more to be added)
	'''
	index = index.upper()
	if index not in HSI_DICT.keys():
		raise HTTPException(status_code = 404, detail = f'invalid index: {index}; must be one of {HSI_DICT.keys()}')
	url = HSI_DICT[index]['xls_url']
	name = HSI_DICT[index]['name']
	df = get_hangseng_constituent_df(xls_url = url, convert_stock_code = True)
	return {'index': index, 'name': name, 'constituents': df.to_dict(orient = 'records')}

@app.get(app_name + "/{ticker}/lotsize",
	response_model = LotSizeResult, response_model_exclude_unset = True)
async def lookup_lot_size(ticker):
	'''get lot size (minimum trading unit)

	* `ticker`: numeric stock code (5) or yahoo (5.hk) or Bloomberg format (e.g. 5 HK)
	'''
	ticker =  parse_hk_ticker(ticker, allow_invalid = True)
	if not ticker:
		raise HTTPException(status_code = 404, detail = f"invalid ticker: {ticker}")
	lot_size = get_lot_size(ticker)
	return {'ticker': ticker, 'lot_size': lot_size}

@app.get(app_name + "/{ticker}/dividends",
	response_model = DivResult, response_model_exclude_unset = True)
async def get_dividends(ticker, ex_date_after = '1/1/2020'):
	'''get dividend history, including upcoming

	* `ticker`: numeric stock code (5) or yahoo (5.hk) or Bloomberg format (e.g. 5 HK)
	* `ex_date_after`: only show history after this date, in mm/dd/yyyy format
	'''
	ticker =  parse_hk_ticker(ticker, allow_invalid = True)
	if not ticker:
		raise HTTPException(status_code = 404, detail = f"invalid ticker: {ticker}")
	df = scrap_hk_stock_div(ticker, ex_date_after = ex_date_after)
	return {'ticker': ticker, 'dividends': df.to_dict(orient = 'records')}

@app.get(f"{app_name}" if app_name else '/')
def read_root():
	return {"HKStocks API": app_version,
			'status': 'Healthy',
			'message': f'see {app_name}/docs/ endpoint for help',
			}
