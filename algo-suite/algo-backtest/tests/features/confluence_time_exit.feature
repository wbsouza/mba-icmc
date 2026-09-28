Feature: Time exit — the causal bar-count expiry as a pure lifecycle (story 21, T6)
  Proves `chain/time_exit.py`, the LEAN-free lifecycle behind `capital_mgmt.exit_after_bars`
  (spec CC-15..CC-19, CC-28, CC-31; decisions D5, D6, D11 as accepted by the user on
  2026-09-28). It receives actual events — the entry fill, each distinct completed candle,
  tradable quotes, order submissions and order statuses, stop fills, same-side signals and
  reversal fills — and answers each tradable event with at most one *closure request*
  (an expiry intent). It never invents a fill: prices, fill times and order ids come from
  the engine that submits the order (T13).

  Accepted timing (D5). Let t be the signal bar during which the entry filled: the
  completed candle whose `[start, end)` contains the fill time; t counts even when the
  fill is mid-bar, and a fill exactly at a candle's end belongs to the next candle. The
  exit is at the open of bar t+N. Expiry becomes DUE when candle t+N-1 completes, at its
  end time (the open of t+N); the lifecycle requests one closure on the first delivered
  tradable event whose timestamp is at or after that time. N = 4 spans the four closes
  of the horizon check; four H1 bars are four scheduled hours, four H4 bars sixteen, and
  a market gap (weekend, daily break) extends elapsed time because only completed
  candles count (CC-28). Partial buckets are never delivered as candles and never count.

  Precedence and identity (D6, D11). A stop fill is reconciled before the expiry: a full
  stop fill closes the trade with reason "stop" and nothing is requested; a partial stop
  fill leaves only the residual quantity eligible. A same-side signal does not reset the
  age; a filled reversal closes the old trade with reason "reversal" and starts a new
  identity whose bar t is the candle containing the reversal fill. A live close order
  blocks a second request; a confirmed rejection or cancellation returns the trade to
  DUE, and the retry waits for a *later* real event, never the same one. Repeated
  identical events are idempotent. The event that carries a closure request suppresses
  new entry on that same event (CC-19). A trade still HOLDING, DUE or PENDING when the
  stream ends is reported unresolved, never closed by assumption.

  States: HOLDING (entry filled, counting candles), DUE (expiry due, no live order),
  PENDING (a close order is live), CLOSED (reason "expiry", "stop" or "reversal").
  Closure quantities are signed order quantities: a +1000 long is closed by -1000.
  The exit record (CC-31) carries: trade_id, clock_minutes, exit_after_bars,
  entry_fill_time, completed_bars, due_at, submitted_at, order_id, order_status,
  fill_time, fill_quantity, fill_price, remaining_quantity, rejections, reason, status;
  anything not yet observed is null, with `status` saying why.

  Rule: The exit is at the open of bar t+N, counted from the candle containing the fill (CC-15, CC-16)

    Scenario Outline: on the <clock>-minute clock a fill at <fill_time> is due at <due_at> and closes on the first event at or after it (<case>)
      Given a time-exit lifecycle on a <clock>-minute clock with exit_after_bars <n>
      And the entry of trade "T1" filled at "<fill_time>" for 1000 units
      And completed candles on the clock from "<first_start>" through "<last_start>"
      When a tradable event arrives at "<event>"
      Then the lifecycle requests one closure of trade "T1" for -1000 units at "<event>"
      And the expiry of trade "T1" is due at "<due_at>"
      And the lifecycle has counted <n> completed bars for trade "T1"
      And the lifecycle suppresses new entry at "<event>"

      Examples:
        | case                                   | clock | n | fill_time            | first_start          | last_start           | due_at               | event                |
        | H1, fill exactly at the open of t      | 60    | 4 | 2016-03-01T10:00:00Z | 2016-03-01T10:00:00Z | 2016-03-01T13:00:00Z | 2016-03-01T14:00:00Z | 2016-03-01T14:00:00Z |
        | H1, fill thirty seconds into t         | 60    | 4 | 2016-03-01T10:00:30Z | 2016-03-01T10:00:00Z | 2016-03-01T13:00:00Z | 2016-03-01T14:00:00Z | 2016-03-01T14:00:00Z |
        | H1, fill in the last minute of t       | 60    | 4 | 2016-03-01T10:59:00Z | 2016-03-01T10:00:00Z | 2016-03-01T13:00:00Z | 2016-03-01T14:00:00Z | 2016-03-01T14:00:00Z |
        | H1, fill exactly at a close is the next bar | 60 | 4 | 2016-03-01T11:00:00Z | 2016-03-01T11:00:00Z | 2016-03-01T14:00:00Z | 2016-03-01T15:00:00Z | 2016-03-01T15:00:00Z |
        | H1, the first event is seven seconds late | 60 | 4 | 2016-03-01T10:00:30Z | 2016-03-01T10:00:00Z | 2016-03-01T13:00:00Z | 2016-03-01T14:00:00Z | 2016-03-01T14:00:07Z |
        | H1, N=1 closes at the open of t+1      | 60    | 1 | 2016-03-01T10:00:30Z | 2016-03-01T10:00:00Z | 2016-03-01T10:00:00Z | 2016-03-01T11:00:00Z | 2016-03-01T11:00:00Z |
        | H4, fill exactly at the open of t      | 240   | 4 | 2016-03-01T00:00:00Z | 2016-03-01T00:00:00Z | 2016-03-01T12:00:00Z | 2016-03-01T16:00:00Z | 2016-03-01T16:00:00Z |
        | H4, fill 77 minutes into t             | 240   | 4 | 2016-03-01T01:17:00Z | 2016-03-01T00:00:00Z | 2016-03-01T12:00:00Z | 2016-03-01T16:00:00Z | 2016-03-01T16:00:00Z |
        | H4, four bars span sixteen scheduled hours | 240 | 4 | 2016-03-01T03:59:00Z | 2016-03-01T00:00:00Z | 2016-03-01T12:00:00Z | 2016-03-01T16:00:00Z | 2016-03-01T16:00:00Z |

    Scenario: the historical bar open is never assigned as a fill; the record waits for the executor
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:07Z"
      And the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:07Z"
      Then trade "T1" is "PENDING"
      And the exit record of trade "T1" is:
        | field              | value                     |
        | trade_id           | T1                        |
        | clock_minutes      | 60                        |
        | exit_after_bars    | 4                         |
        | entry_fill_time    | 2016-03-01T10:00:30+00:00 |
        | completed_bars     | 4                         |
        | due_at             | 2016-03-01T14:00:00+00:00 |
        | submitted_at       | 2016-03-01T14:00:07+00:00 |
        | order_id           | 7                         |
        | order_status       | SUBMITTED                 |
        | fill_time          | null                      |
        | fill_quantity      | null                      |
        | fill_price         | null                      |
        | remaining_quantity | 1000                      |
        | rejections         | 0                         |
        | reason             | null                      |
        | status             | PENDING                   |

    Scenario: an event before the due time requests nothing, and the count advances only with completed candles
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T12:00:00Z"
      When a tradable event arrives at "2016-03-01T13:59:59Z"
      Then the lifecycle requests no closure
      And the lifecycle has counted 3 completed bars for trade "T1"
      And trade "T1" is "HOLDING"
      And the expiry of trade "T1" is not yet due
      And the lifecycle does not suppress new entry at "2016-03-01T13:59:59Z"
      When the completed candle "2016-03-01T13:00:00Z".."2016-03-01T14:00:00Z" is delivered
      Then trade "T1" is "DUE"
      And the expiry of trade "T1" is due at "2016-03-01T14:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      Then the lifecycle requests one closure of trade "T1" for -1000 units at "2016-03-01T14:00:00Z"

    Scenario: a weekend gap extends the elapsed time because only completed candles count (CC-28)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-04T19:00:30Z" for 1000 units
      And the completed candle "2016-03-04T19:00:00Z".."2016-03-04T20:00:00Z" is delivered
      And the completed candle "2016-03-04T20:00:00Z".."2016-03-04T21:00:00Z" is delivered
      When a tradable event arrives at "2016-03-04T21:30:00Z"
      Then the lifecycle requests no closure
      And the lifecycle has counted 2 completed bars for trade "T1"
      When a tradable event arrives at "2016-03-06T22:05:00Z"
      Then the lifecycle requests no closure
      And the lifecycle has counted 2 completed bars for trade "T1"
      When the completed candle "2016-03-06T23:00:00Z".."2016-03-07T00:00:00Z" is delivered
      And the completed candle "2016-03-07T00:00:00Z".."2016-03-07T01:00:00Z" is delivered
      Then the expiry of trade "T1" is due at "2016-03-07T01:00:00Z"
      When a tradable event arrives at "2016-03-07T01:00:00Z"
      Then the lifecycle requests one closure of trade "T1" for -1000 units at "2016-03-07T01:00:00Z"
      And the elapsed time from the entry fill to the closure request is 53 hours 59 minutes 30 seconds

  Rule: Partial buckets are never counted; malformed candles are refused (CC-15)

    Scenario Outline: a candle that is not one complete clock period is refused and the count is unchanged (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-04T19:00:30Z" for 1000 units
      And the completed candle "2016-03-04T19:00:00Z".."2016-03-04T20:00:00Z" is delivered
      When the candle "<start>".."<end>" is delivered and refused
      Then the time-exit failure names "<fragment>"
      And the lifecycle has counted 1 completed bars for trade "T1"

      Examples:
        | case                              | start                | end                  | fragment                                   |
        | a 58-minute partial bucket        | 2016-03-04T21:00:00Z | 2016-03-04T21:58:00Z | is not one complete 60-minute candle       |
        | a candle off the clock grid       | 2016-03-04T20:30:00Z | 2016-03-04T21:30:00Z | is not on the 60-minute UTC grid           |
        | a candle ending before the last   | 2016-03-04T18:00:00Z | 2016-03-04T19:00:00Z | is not after the last completed candle     |
        | a naive candle time               | 2016-03-04T20:00:00  | 2016-03-04T21:00:00  | must be timezone-aware UTC                 |
        | a 120-minute double bucket        | 2016-03-04T20:00:00Z | 2016-03-04T22:00:00Z | is not one complete 60-minute candle       |

    Scenario: a candle completed before the entry fill does not count toward the trade
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the completed candle "2016-03-01T09:00:00Z".."2016-03-01T10:00:00Z" is delivered
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      When the completed candle "2016-03-01T10:00:00Z".."2016-03-01T11:00:00Z" is delivered
      Then the lifecycle has counted 1 completed bars for trade "T1"

  Rule: Repeated identical events are idempotent (CC-18)

    Scenario: the same completed candle delivered twice counts once
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And the completed candle "2016-03-01T10:00:00Z".."2016-03-01T11:00:00Z" is delivered
      When the completed candle "2016-03-01T10:00:00Z".."2016-03-01T11:00:00Z" is delivered
      Then the lifecycle has counted 1 completed bars for trade "T1"

    Scenario: the same entry fill reported twice is one trade with one age
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And the completed candle "2016-03-01T10:00:00Z".."2016-03-01T11:00:00Z" is delivered
      When the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units is reported again
      Then the lifecycle has counted 1 completed bars for trade "T1"
      And trade "T1" is "HOLDING"
      And the lifecycle tracks exactly the trades "T1"

    Scenario: the same tradable event delivered twice requests one closure, not two
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      Then the lifecycle requests one closure of trade "T1" for -1000 units at "2016-03-01T14:00:00Z"
      When the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:00Z"
      And a tradable event arrives at "2016-03-01T14:00:00Z"
      Then the lifecycle requests no closure
      And the lifecycle has requested 1 closures in total

  Rule: Same-side signals do not reset the age; a filled reversal starts a new identity (CC-18, D6)

    Scenario: a same-side signal leaves the count and the due time untouched
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T11:00:00Z"
      When a same-side signal arrives at "2016-03-01T12:00:00Z"
      And completed candles on the clock from "2016-03-01T12:00:00Z" through "2016-03-01T13:00:00Z"
      Then the lifecycle has counted 4 completed bars for trade "T1"
      And the expiry of trade "T1" is due at "2016-03-01T14:00:00Z"
      And the lifecycle tracks exactly the trades "T1"

    Scenario: a filled reversal closes the old trade and starts counting the new one from its own bar t
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T11:00:00Z"
      When the reversal filled at "2016-03-01T12:00:00Z" closing trade "T1" and opening trade "T2" for -1000 units
      Then trade "T1" is "CLOSED" with reason "reversal"
      And trade "T2" is "HOLDING"
      And the lifecycle has counted 0 completed bars for trade "T2"
      When completed candles on the clock from "2016-03-01T12:00:00Z" through "2016-03-01T15:00:00Z"
      Then the lifecycle has counted 4 completed bars for trade "T2"
      And the expiry of trade "T2" is due at "2016-03-01T16:00:00Z"
      When a tradable event arrives at "2016-03-01T16:00:00Z"
      Then the lifecycle requests one closure of trade "T2" for 1000 units at "2016-03-01T16:00:00Z"

  Rule: A stop fill is reconciled before the expiry (CC-17)

    Scenario Outline: a full stop fill at <stop_time> closes the trade with reason "stop" and no closure is requested (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "<last_start>"
      When the stop of trade "T1" filled at "<stop_time>" for -1000 units at price 1.0980
      And a tradable event arrives at "2016-03-01T14:00:00Z"
      Then the lifecycle requests no closure
      And trade "T1" is "CLOSED" with reason "stop"
      And the exit record of trade "T1" has fill_time "<stop_time>", fill_quantity -1000 and fill_price 1.098
      And the lifecycle does not suppress new entry at "2016-03-01T14:00:00Z"

      Examples:
        | case                                            | last_start           | stop_time            |
        | the stop fills before the horizon               | 2016-03-01T11:00:00Z | 2016-03-01T11:30:00Z |
        | the stop fills at the due time, ahead of expiry | 2016-03-01T13:00:00Z | 2016-03-01T14:00:00Z |

    Scenario: a brand new entry is accepted immediately after a full stop fill closes the prior trade
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      When the stop of trade "T1" filled at "2016-03-01T11:30:00Z" for -1000 units at price 1.0980
      And the entry of trade "T2" filled at "2016-03-01T11:31:00Z" for 500 units
      Then trade "T2" is "HOLDING"
      And the lifecycle tracks exactly the trades "T1, T2"

    Scenario Outline: a partial stop fill of <stop_quantity> leaves <remaining> units eligible for the expiry (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When the stop of trade "T1" filled at "<stop_time>" for <stop_quantity> units at price 1.0980
      Then the remaining quantity of trade "T1" is <remaining>
      And trade "T1" is "<state_after_stop>"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      Then the lifecycle requests one closure of trade "T1" for <closure> units at "2016-03-01T14:00:00Z"

      Examples:
        | case                                      | stop_time            | stop_quantity | remaining | state_after_stop | closure |
        | a partial stop before the horizon         | 2016-03-01T11:30:00Z | -400          | 600       | DUE              | -600    |
        | a partial stop at the due time, first     | 2016-03-01T14:00:00Z | -250          | 750       | DUE              | -750    |

    Scenario: a stop fill larger than the position is refused as inconsistent
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      When the stop of trade "T1" filled at "2016-03-01T11:30:00Z" for -1500 units at price 1.0980 and is refused
      Then the time-exit failure names "exceeds the remaining 1000 units of trade 'T1'"

  Rule: One live close order at a time; a confirmed rejection allows a retry on a later real event (CC-16, CC-18)

    Scenario: a live close order blocks a second request until its status is confirmed
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:00Z"
      And a tradable event arrives at "2016-03-01T14:01:00Z"
      Then the lifecycle requests no closure
      And trade "T1" is "PENDING"
      When a tradable event arrives at "2016-03-01T14:02:00Z"
      Then the lifecycle requests no closure
      And the lifecycle has requested 1 closures in total
      When the engine reports close order 7 "filled" at "2016-03-01T14:02:00Z" for -1000 units at price 1.1010
      Then trade "T1" is "CLOSED" with reason "expiry"
      And the exit record of trade "T1" has fill_time "2016-03-01T14:02:00Z", fill_quantity -1000 and fill_price 1.101
      And the remaining quantity of trade "T1" is 0
      When the entry of trade "T2" filled at "2016-03-01T14:03:00Z" for 500 units
      Then trade "T2" is "HOLDING"
      And the lifecycle tracks exactly the trades "T1, T2"

    Scenario Outline: a <status> close order returns the trade to DUE and the retry waits for a later real event (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 "<status>" at "2016-03-01T14:00:00Z"
      Then trade "T1" is "DUE"
      And the exit record of trade "T1" has rejections 1 and order_status "<recorded>"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      Then the lifecycle requests no closure
      When a tradable event arrives at "2016-03-01T14:01:00Z"
      Then the lifecycle requests one closure of trade "T1" for -1000 units at "2016-03-01T14:01:00Z"
      And the lifecycle suppresses new entry at "2016-03-01T14:01:00Z"
      When the engine reports close order 8 submitted for trade "T1" at "2016-03-01T14:01:00Z"
      And the engine reports close order 8 "filled" at "2016-03-01T14:01:00Z" for -1000 units at price 1.1010
      Then trade "T1" is "CLOSED" with reason "expiry"
      And the exit record of trade "T1" has order_id 8, rejections 1 and order_status "FILLED"

      Examples:
        | case                    | status   | recorded |
        | a rejected close order  | rejected | REJECTED |
        | a cancelled close order | canceled | CANCELED |

    Scenario: a status for an order the lifecycle never submitted is refused
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      When the engine reports close order 9 "filled" at "2016-03-01T14:00:00Z" for -1000 units at price 1.1010 and is refused
      Then the time-exit failure names "order 9 is not the live close order of trade 'T1'"

    Scenario: an order status report with an unrecognized status is refused
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 "expired" at "2016-03-01T14:00:00Z" for -1000 units at price 1.1010 and is refused
      Then the time-exit failure names "unknown order status 'expired' for trade 'T1'"

  Rule: The expiry-submission event suppresses new entry on that event only (CC-19)

    Scenario Outline: new entry is <suppressed> at <event> (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 "filled" at "2016-03-01T14:00:00Z" for -1000 units at price 1.1010
      And a tradable event arrives at "2016-03-01T14:01:00Z"
      Then new entry is <suppressed> at "<event>"

      Examples:
        | case                                     | event                | suppressed     |
        | the event that carried the request       | 2016-03-01T14:00:00Z | suppressed     |
        | the next event after the fill            | 2016-03-01T14:01:00Z | not suppressed |

  Rule: End-of-stream state stays visibly unresolved (CC-18, CC-31)

    Scenario Outline: a trade still <state> when the stream ends is reported unresolved (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "<last_start>"
      And the following happens: <events>
      When the event stream ends
      Then trade "T1" is "<state>"
      And the unresolved trades are "T1"
      And the exit record of trade "T1" has status "<state>", reason null and fill_time null

      Examples:
        | case                                  | last_start           | events                                                                                                  | state   |
        | a live close order with no status     | 2016-03-01T13:00:00Z | an event at 2016-03-01T14:00:00Z, then close order 7 submitted at 2016-03-01T14:00:00Z                  | PENDING |
        | due with no later event               | 2016-03-01T13:00:00Z | nothing                                                                                                 | DUE     |
        | still counting                        | 2016-03-01T11:00:00Z | nothing                                                                                                 | HOLDING |

    Scenario: a closed trade is not unresolved and a flat lifecycle has nothing to report
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And completed candles on the clock from "2016-03-01T10:00:00Z" through "2016-03-01T13:00:00Z"
      When a tradable event arrives at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 submitted for trade "T1" at "2016-03-01T14:00:00Z"
      And the engine reports close order 7 "filled" at "2016-03-01T14:00:00Z" for -1000 units at price 1.1010
      And the event stream ends
      Then the unresolved trades are none
      And the exit record of trade "T1" is:
        | field              | value                     |
        | trade_id           | T1                        |
        | clock_minutes      | 60                        |
        | exit_after_bars    | 4                         |
        | entry_fill_time    | 2016-03-01T10:00:30+00:00 |
        | completed_bars     | 4                         |
        | due_at             | 2016-03-01T14:00:00+00:00 |
        | submitted_at       | 2016-03-01T14:00:00+00:00 |
        | order_id           | 7                         |
        | order_status       | FILLED                    |
        | fill_time          | 2016-03-01T14:00:00+00:00 |
        | fill_quantity      | -1000                     |
        | fill_price         | 1.101                     |
        | remaining_quantity | 0                         |
        | rejections         | 0                         |
        | reason             | expiry                    |
        | status             | CLOSED                    |
      And the exit record of trade "T1" round-trips through plain JSON-safe values

  Rule: Invalid construction and inconsistent events fail fast naming the fix

    Scenario Outline: a lifecycle with <case> is refused
      When a time-exit lifecycle on a <clock>-minute clock with exit_after_bars <n> is built and refused
      Then the time-exit failure names "<fragment>"

      Examples:
        | case                        | clock | n     | fragment                                       |
        | exit_after_bars zero        | 60    | 0     | exit_after_bars must be a positive integer     |
        | exit_after_bars negative    | 60    | -4    | exit_after_bars must be a positive integer     |
        | a boolean exit_after_bars   | 60    | true  | exit_after_bars must be a positive integer     |
        | a fractional exit_after_bars| 60    | 4.5   | exit_after_bars must be a positive integer     |
        | a zero clock                | 0     | 4     | clock_minutes must be a positive integer       |

    Scenario Outline: an inconsistent event is refused and the lifecycle is unchanged (<case>)
      Given a time-exit lifecycle on a 60-minute clock with exit_after_bars 4
      And the entry of trade "T1" filled at "2016-03-01T10:00:30Z" for 1000 units
      And the completed candle "2016-03-01T10:00:00Z".."2016-03-01T11:00:00Z" is delivered
      When <event> and it is refused
      Then the time-exit failure names "<fragment>"
      And the lifecycle has counted 1 completed bars for trade "T1"
      And trade "T1" is "HOLDING"

      Examples:
        | case                                   | event                                                                              | fragment                                        |
        | a second entry while T1 is open        | the entry of trade "T2" filled at "2016-03-01T11:30:00Z" for 1000 units            | trade 'T1' is still open                        |
        | a zero-quantity entry                  | the entry of trade "T3" filled at "2016-03-01T11:30:00Z" for 0 units               | quantity must be a nonzero number               |
        | a tradable event before the last time  | a tradable event arrives at "2016-03-01T10:59:00Z"                                 | is not at or after the last processed time      |
        | a naive event time                     | a tradable event arrives at "2016-03-01T11:30:00"                                  | must be timezone-aware UTC                      |
        | a stop fill for an unknown trade       | the stop of trade "T9" filled at "2016-03-01T11:30:00Z" for -100 units at price 1.0 | trade 'T9' is not open                          |
