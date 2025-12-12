from pytest_bdd import given, when, then, parsers
import pytest
from src.core.compliance_engine import ComplianceEngine
# 假設你的核心引擎類別

# 使用 pytest.fixture 來初始化資源，供所有測試使用
@pytest.fixture
def compliance_engine():
    # 這裡可以初始化你的資料庫連線、載入模擬的法規資料等
    return ComplianceEngine(mode='test')

# 對應第一個 Scenario 的 Given 步驟
@given("the system has successfully loaded the latest global regulatory list including EU REACH")
def load_regulatory_data(compliance_engine):
    """確保法規資料已載入，並且是可用的最新版本。"""
    # 實際程式碼：調用你的數據載入函數
    assert compliance_engine.load_data(source='REACH_latest') is True

# 對應第二個 Given 步驟
@given(parsers.parse('the user inputs the chemical name: "{chemical_name}"'))
def set_chemical_name(scenario_context, chemical_name):
    """將化學品名稱儲存在測試情境上下文中。"""
    scenario_context['chemical'] = chemical_name

# 對應 When 步驟
@when(parsers.parse('the AI agent performs a compliance diagnosis and specifies the target market as "{market}"'))
def perform_diagnosis(scenario_context, compliance_engine, market):
    """執行實際的法規診斷邏輯。"""
    chemical = scenario_context['chemical']
    # 實際程式碼：調用核心診斷函數
    scenario_context['result'] = compliance_engine.run_diagnosis(chemical, market)

# 對應 Then 步驟
@then(parsers.parse('the system should return a clear status of "{expected_status}" within 30 seconds'))
def check_status(scenario_context, expected_status):
    """驗證回傳的狀態是否符合預期。"""
    # 這裡可以加入時間測量邏輯
    assert scenario_context['result']['status'] == expected_status

# ... 依此類推撰寫所有 Given/When/Then 的步驟函數 ...