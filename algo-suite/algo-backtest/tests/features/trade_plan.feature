Feature: Trade-plan math turns an F7 signal into the orders the executor places
  Story 12 (execution realism), item D. F6 enriches `state.features["trade_plan"]` with the
  fx-manager A05 plan in pips (one block per direction); `engine/trade_plan.py` converts it,
  at the entry fill, into a signed quantity, a stop price and per-target prices/quantities,
  then manages the open position (trailing steps that fire once, the minimum hold) and
  reconciles the working orders when one fills (OCO emulation). LEAN-free, so every rule is
  proven here with tables; the LEAN glue (`engine/chain_algorithm.py`) is covered by the
  `@integration` scenarios of run_baseline_chain.feature.

  Rule: The entry quantity is the plan's lot size in units, signed by direction

    Scenario Outline: <lot_size> lots of <lot_notional_units> units to <direction> is <quantity> units
      When the order quantity is computed for <lot_size> lots of <lot_notional_units> units to <direction>
      Then the quantity is <quantity>

      Examples:
        | lot_size | lot_notional_units | direction | quantity |
        | 1.5      | 100000             | BUY       | 150000   |
        | 0.25     | 100000             | SELL      | -25000   |
        | 1        | 1000               | BUY       | 1000     |

    Scenario Outline: a non-positive <what> is a sizing failure, not an order (<lot_size> × <lot_notional_units>)
      When computing the order quantity for <lot_size> lots of <lot_notional_units> units to BUY fails
      Then the trade-plan failure names "<what> must be > 0"

      Examples:
        | what               | lot_size | lot_notional_units |
        | lot_size           | 0        | 100000             |
        | lot_size           | -0.5     | 100000             |
        | lot_notional_units | 1.0      | 0                  |

    Scenario Outline: quantities snap toward zero to the instrument's lot step (<quantity> by <lot_step>)
      When <quantity> units are rounded to a lot step of <lot_step>
      Then the rounded quantity is <rounded>

      Examples:
        | quantity  | lot_step | rounded |
        | 149999.9  | 1        | 149999  |
        | -25000.7  | 1        | -25000  |
        | 12345     | 1000     | 12000   |
        | -12345    | 1000     | -12000  |
        | 0.4       | 1        | 0       |
        | 150000    | 1        | 150000  |

  Rule: The stop sits stop_pips against the trade and the targets stop_pips in its favour

    Scenario Outline: stop price for a <direction> at <entry> with <stop_pips> pips of <pip_size>
      When the stop price is computed for a <direction> at <entry> with stop <stop_pips> pips and pip size <pip_size>
      Then the stop price is <stop> within 1e-9

      Examples:
        | direction | entry   | stop_pips | pip_size | stop    |
        | BUY       | 1.10000 | 20        | 0.0001   | 1.09800 |
        | SELL      | 1.10000 | 20        | 0.0001   | 1.10200 |
        | BUY       | 110.000 | 20        | 0.01     | 109.800 |
        | SELL      | 1.10000 | 2.5       | 0.0001   | 1.10025 |

    Scenario Outline: a non-positive stop distance or pip size fails fast (<stop_pips> pips of <pip_size>)
      When computing the stop price for a BUY at 1.1 with stop <stop_pips> pips and pip size <pip_size> fails
      Then the trade-plan failure names "<what> must be > 0"

      Examples:
        | stop_pips | pip_size | what      |
        | 0         | 0.0001   | stop_pips |
        | 20        | 0        | pip_size  |

    Scenario Outline: target prices for a <direction> at <entry> (<targets>)
      When the target prices are computed for a <direction> at <entry> with targets <targets> and pip size 0.0001
      Then the target prices are <prices> within 1e-9

      Examples:
        | direction | entry   | targets                                            | prices                          |
        | BUY       | 1.10000 | [{pips: 10, close_fraction: 0.5}, {pips: 20, close_fraction: 0.5}] | [[1.10100, 0.5], [1.10200, 0.5]] |
        | SELL      | 1.10000 | [{pips: 10, close_fraction: 0.5}, {pips: 20, close_fraction: 0.5}] | [[1.09900, 0.5], [1.09800, 0.5]] |
        | BUY       | 1.10000 | [{pips: 43, close_fraction: 1.0}]                   | [[1.10430, 1.0]]                |
        | BUY       | 1.10000 | []                                                 | []                              |

  Rule: Each target closes its fraction of the entry quantity; the last full-close target takes the remainder

    Scenario Outline: exits for a position of <quantity> with fractions <fractions> at lot step <lot_step>
      When the target quantities are computed for a position of <quantity> with fractions <fractions> and lot step <lot_step>
      Then the target quantities are <exits>

      Examples:
        | quantity | fractions       | lot_step | exits                    |
        | 100000   | [0.5, 0.5]      | 1        | [-50000, -50000]         |
        | -100000  | [0.5, 0.5]      | 1        | [50000, 50000]           |
        | 100001   | [0.5, 0.5]      | 1        | [-50000, -50001]         |
        | 100000   | [0.3, 0.3, 0.4] | 1        | [-30000, -30000, -40000] |
        | 100000   | [0.5]           | 1        | [-50000]                 |
        | 13000    | [0.5, 0.5]      | 1000     | [-6000, -7000]           |
        | 100000   | []              | 1        | []                       |

    Scenario Outline: an exit ladder that cannot be placed fails fast (<case>)
      When computing the target quantities for a position of <quantity> with fractions <fractions> and lot step <lot_step> fails
      Then the trade-plan failure names "<failure>"

      Examples:
        | case                   | quantity | fractions  | lot_step | failure                          |
        | flat position          | 0        | [0.5]      | 1        | non-zero position quantity       |
        | off the lot step       | 12345    | [0.5, 0.5] | 1000     | not a multiple of lot_step       |
        | fractions past 1       | 100000   | [0.6, 0.6] | 1        | over-close                       |

  Rule: A trailing step arms once its favourable move is reached and only ever tightens the stop

    Scenario Outline: trail check for a <direction> from <entry> now at <current>, stop <current_stop> (<case>)
      Given the trailing steps <steps> with pip size 0.0001
      And the steps already fired are <fired>
      When the trail is checked for a <direction> entered at <entry> now at <current> with stop <current_stop>
      Then the trail outcome is <outcome> with new stop <new_stop> and fired steps <newly_fired>

      Examples:
        | case                        | direction | entry   | current | current_stop | steps                              | fired | outcome | new_stop | newly_fired |
        | arms and tightens (long)    | BUY       | 1.10000 | 1.10100 | 1.09800      | [{at_pips: 10, to_pips: -5}]       | []    | move    | 1.09950  | [0]         |
        | not yet armed (long)        | BUY       | 1.10000 | 1.10050 | 1.09800      | [{at_pips: 10, to_pips: -5}]       | []    | none    | null     | []          |
        | already fired (long)        | BUY       | 1.10000 | 1.10200 | 1.09950      | [{at_pips: 10, to_pips: -5}]       | [0]   | none    | null     | []          |
        | armed but looser (long)     | BUY       | 1.10000 | 1.10100 | 1.09980      | [{at_pips: 10, to_pips: -5}]       | []    | consume | null     | [0]         |
        | arms and tightens (short)   | SELL      | 1.10000 | 1.09900 | 1.10200      | [{at_pips: 10, to_pips: -5}]       | []    | move    | 1.10050  | [0]         |
        | profit-side lock-in (long)  | BUY       | 1.10000 | 1.10200 | 1.09800      | [{at_pips: 20, to_pips: 2}]        | []    | move    | 1.10020  | [0]         |
        | two steps arm, tightest wins| BUY       | 1.10000 | 1.10300 | 1.09800      | [{at_pips: 10, to_pips: -5}, {at_pips: 30, to_pips: 5}] | [] | move | 1.10050 | [0, 1] |
        | second step after the first | BUY       | 1.10000 | 1.10300 | 1.09950      | [{at_pips: 10, to_pips: -5}, {at_pips: 30, to_pips: 5}] | [0] | move | 1.10050 | [1] |
        | adverse move never arms     | SELL      | 1.10000 | 1.10100 | 1.10200      | [{at_pips: 10, to_pips: -5}]       | []    | none    | null     | []          |

  Rule: An opposite signal may close the position only once the minimum hold has elapsed

    Scenario Outline: entered at bar <entry_bar>, now bar <now>, min hold <min_hold_bars> → <elapsed>
      When the hold is checked for entry bar <entry_bar> at bar <now> with min hold <min_hold_bars>
      Then the hold elapsed is <elapsed>

      Examples:
        | entry_bar | now | min_hold_bars | elapsed |
        | 10        | 10  | 0             | true    |
        | 10        | 12  | 3             | false   |
        | 10        | 13  | 3             | true    |
        | 10        | 20  | 3             | true    |

    Scenario Outline: an impossible hold check fails fast (entry <entry_bar>, now <now>, hold <min_hold_bars>)
      When checking the hold for entry bar <entry_bar> at bar <now> with min hold <min_hold_bars> fails
      Then the trade-plan failure names "<failure>"

      Examples:
        | entry_bar | now | min_hold_bars | failure                   |
        | 10        | 9   | 0             | precedes entry_bar_index  |
        | 10        | 10  | -1            | min_hold_bars must be >= 0|

  Rule: Once the position is flat every working order is cancelled; a partial exit resizes the stop

    Scenario Outline: position <position> with working orders <orders> cancels <cancelled>
      When the orders to cancel are computed for a position of <position> with working orders <orders>
      Then the orders to cancel are <cancelled>

      Examples:
        | position | orders                     | cancelled |
        | 0        | [[7, -50000], [8, -50000]] | [7, 8]    |
        | 50000    | [[7, -50000], [8, -50000]] | []        |
        | 0        | []                         | []        |
        | -50000   | [[7, 100000]]              | []        |

    Scenario Outline: the stop after a partial exit closes exactly the remaining <position>
      When the stop quantity is computed for a remaining position of <position>
      Then the stop quantity is <stop_quantity>

      Examples:
        | position | stop_quantity |
        | 50000    | -50000        |
        | -25000   | 25000         |

    Scenario: a flat position has no stop to resize
      When computing the stop quantity for a remaining position of 0 fails
      Then the trade-plan failure names "needs an open position"

  Rule: The executor's memory of the open trade consumes fired steps and adopts a tightened stop

    Scenario Outline: a planned position applies a trail move (<case>)
      Given a planned BUY position with stop <stop_before> whose fired steps are <fired_before>
      When the trail move firing <fired> with new stop <new_stop> is applied to it
      Then the position's fired steps are <fired_after> and its stop is <stop_after>

      Examples:
        | case                     | stop_before | fired_before | fired | new_stop | fired_after | stop_after |
        | first step tightens      | 1.09800     | []           | [0]   | 1.09950  | [0]         | 1.09950    |
        | armed but looser: consumed only | 1.09800 | [0]        | [1]   | null     | [0, 1]      | 1.09800    |
        | both steps at once       | 1.09800     | []           | [0, 1]| 1.10050  | [0, 1]      | 1.10050    |

  Rule: F6's trade_plan feature is read as typed blocks and its absence is a chain misconfiguration

    Scenario: a complete trade_plan feature parses into the long and short plans
      Given a trade_plan feature with lot_size 1.5 and spread 1.0 whose long stop is 16 pips with targets [{pips: 35, close_fraction: 0.5}] and trail [{at_pips: 9.5, to_pips: -9.56}]
      When the trade plan is parsed
      Then the parsed plan has lot_size 1.5, spread 1.0, long stop 16 pips, 1 long target and 1 long trail step
      And the parsed long block for BUY is the long plan

    Scenario: a missing trade_plan feature names F6 and the contract
      Given features without a trade_plan
      When parsing the trade plan fails
      Then the trade-plan failure names "f6_capital_mgmt"
      And the trade-plan failure names "trade_plan"

    Scenario Outline: a trade_plan block missing <key> fails naming it
      Given a trade_plan feature whose long block lacks "<key>"
      When parsing the trade plan fails
      Then the trade-plan failure names "<key>"

      Examples:
        | key         |
        | stop_pips   |
        | targets     |
        | trail_stops |
        | reward_risk |

    Scenario Outline: a trade_plan value of the wrong type fails naming its path (<case>)
      Given a trade_plan feature where <path> is set to <value>
      When parsing the trade plan fails
      Then the trade-plan failure names "<failure>"

      Examples:
        | case                          | path                      | value  | failure                                    |
        | the feature is not a mapping  | trade_plan                | 42     | 'trade_plan' must be a mapping             |
        | a block is not a mapping      | trade_plan.long           | [1, 2] | trade_plan.long must be a mapping          |
        | text where a number belongs   | trade_plan.lot_size       | big    | trade_plan.lot_size must be a number       |
        | a flag where a number belongs | trade_plan.long.stop_pips | true   | trade_plan.long.stop_pips must be a number |

  Rule: The trade-plans.json record carries the frozen keys the run statement reads

    Scenario: a record serialises with the contract's keys, ratios and prices
      Given a BUY plan record at 1.10000 for 1.5 lots (150000 units), stop 1.09840, targets [[1.10350, 0.5, -75000]], trail [{at_pips: 9.5, to_pips: -9.56}] over a 16 pip stop, spread 1.0
      When the record is serialised
      Then the serialised record has exactly the keys entry_order_id, entry_time, direction, lots, quantity, entry_price, stop_loss, take_profits, trail_stops, spread_pips
      And the serialised direction is "buy"
      And the serialised take_profits are [{price: 1.10350, close_fraction: 0.5, quantity: -75000}]
      And the serialised trail_stops are [{at_level_ratio: 0.59375, to_level_ratio: -0.5975, at_price: 1.10095, to_price: 1.099044}] within 1e-9
      And the trade-plans document is a JSON list of that one record
