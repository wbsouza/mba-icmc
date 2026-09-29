Feature: Perception boundary validation
  Scenario Outline: Native smoothing periods reject ambiguous input before runtime use
    Given a smoothing period represented by <value>
    When the smoothing period is validated
    Then smoothing validation <outcome>

    Examples:
      | value | outcome |
      | 1     | accepts |
      | 2     | accepts |
      | 0     | rejects |
      | -1    | rejects |
      | true  | rejects |
      | 1.5   | rejects |
      | "2"   | rejects |

  Scenario Outline: Candidate settings preserve custom values or reject non-mappings
    Given perception settings represented by <settings>
    When those candidate settings are parsed
    Then the candidate parse result is <result>

    Examples:
      | settings                                              | result  |
      | {"period1": 1, "period2": 1, "higher_tf_minutes": 2}     | 1,1,2   |
      | {"period1": 9, "period2": 3, "higher_tf_minutes": 120}   | 9,3,120 |
      | null                                                  | rejects |
      | []                                                    | rejects |
      | "wrong"                                               | rejects |

  @integration
  Scenario: Source wiring warms the candidate before allowing chain evaluation
    Given the native strategy source wiring probe
    When EMA and candidate source configurations are exercised
    Then candidate readiness gates the chain and replaces only both trend directions

  Scenario: Direct construction rejects a primary-sized higher timeframe
    Given a direct higher timeframe of one minute
    When the multi-timeframe perception is constructed
    Then construction rejects the timeframe before loading native indicators
