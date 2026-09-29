Feature: LEAN's OANDA forex market hours, mirrored offline
  The pinned LEAN engine delivers a minute bar only while the exchange is open at the
  bar's start (Forex-oanda-[*], New York time). market_hours.lean_delivers mirrors the
  vendored database entry so F7 training sees exactly the bars the backtest sees.

  Scenario Outline: <case>
    Then a bar starting at "<utc>" is <delivered>

    Examples:
      | case                                            | utc                       | delivered     |
      | last minute before the summer daily break       | 2014-05-07T20:57:00+00:00 | delivered     |
      | first minute of the summer daily break          | 2014-05-07T20:58:00+00:00 | not delivered |
      | last minute of the summer daily break           | 2014-05-07T21:02:00+00:00 | not delivered |
      | first minute after the summer daily break       | 2014-05-07T21:03:00+00:00 | delivered     |
      | winter daily break is an hour later in UTC      | 2015-02-25T21:58:00+00:00 | not delivered |
      | winter bar at the summer break's UTC time       | 2015-02-25T20:58:00+00:00 | delivered     |
      | Friday after the weekly close                   | 2015-02-27T21:58:00+00:00 | not delivered |
      | Saturday                                        | 2015-02-28T12:00:00+00:00 | not delivered |
      | Sunday before the weekly open                   | 2015-03-01T22:02:00+00:00 | not delivered |
      | Sunday at the weekly open                       | 2015-03-01T22:03:00+00:00 | delivered     |
      | a listed full holiday                           | 2015-12-25T15:00:00+00:00 | not delivered |
      | before a listed early close                     | 2015-12-31T18:59:00+00:00 | delivered     |
      | at a listed early close                         | 2015-12-31T19:00:00+00:00 | not delivered |
      | a late open keeps the day closed before it      | 2024-12-25T22:04:00+00:00 | not delivered |
      | a late open's first minute                      | 2024-12-25T22:05:00+00:00 | delivered     |
      | a late-open day before its open time            | 2019-01-01T15:00:00+00:00 | not delivered |
      | weekly open on the spring-forward Sunday (EDT)  | 2015-03-08T21:03:00+00:00 | delivered     |
      | an hour earlier on the spring-forward Sunday    | 2015-03-08T21:02:00+00:00 | not delivered |
      | weekly open on the fall-back Sunday (EST)       | 2015-11-01T22:03:00+00:00 | delivered     |
      | the EDT open time on the fall-back Sunday       | 2015-11-01T21:03:00+00:00 | not delivered |
      | daily break the Monday after spring-forward     | 2015-03-09T20:58:00+00:00 | not delivered |
