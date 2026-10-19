


from fastapi import APIRouter

router=APIRouter(prefix='/api/history',tags=['history'])

@router.post('add_history')
async def add_history():
    pass