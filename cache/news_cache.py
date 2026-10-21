from typing import Any, Dict, List, Optional

from config.cache_config import get_json_cache, set_cache


categories_key='news:categories'
news_list_key='news:list:'

async def get_cache_categories():
    return await get_json_cache(categories_key)

async def set_cache_categories(data:List[Dict[str,Any]],expire:int=1200):
    return await set_cache(categories_key,data,expire)


async def set_cache_news_list(
    data: List[Dict[str, Any]],
    category_id: Optional[int],
    page: int,
    size: int,
    expire: int = 300,
):
    category_part=category_id if category_id is not None else 'all'
    key= f'{news_list_key}{category_part}:{page}:{size}'
    return await set_cache(key, data, expire)


async def get_cache_news_list(category_id:int,page:int,size:int):
    category_part = category_id if category_id is not None else "all"
    key = f"{news_list_key}{category_part}:{page}:{size}"
    return await get_json_cache(key)
