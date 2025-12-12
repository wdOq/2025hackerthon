Feature: Regulatory Compliance Diagnosis
  作為一個化學產業管理者，
  我希望 AI 代理人能快速檢查化學品的禁用狀態，
  以便我能立即採取行動，避免營運中斷。

  Scenario: Successful diagnosis of a substance banned by EU REACH
    Given the system has successfully loaded the latest global regulatory list including EU REACH
    And the user inputs the chemical name: "Diisobutyl Phthalate (DIBP)"
    When the AI agent performs a compliance diagnosis and specifies the target market as "EU"
    Then the system should return a clear status of "BANNED" or "AUTHORIZATION_REQUIRED" within 30 seconds
    And the result should include the specific regulatory basis (e.g., REACH Annex XIV)
    And the system should trigger the "alternative search" flow

  Scenario: Quick cross-check for multi-country regulations
    Given the user inputs the chemical name: "Chemical Y"
    And the user specifies target markets as "Taiwan" and "Japan"
    When the AI agent simultaneously compares Taiwan's Toxic and Concerned Chemical Substances Control Act and Japan's Chemical Substance Control Law
    Then the system should generate a cross-comparison report clearly listing the control level differences under both regulations
    And the report should provide a natural language summary of the latest regulatory articles