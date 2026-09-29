Feature: Decode Dukascopy .bi5 hour payloads into UTC ticks
  The binary codec decodes LZMA-compressed >IIIff records, scales prices by the
  instrument's price increment, anchors timestamps to the hour start in UTC, and
  distinguishes the three input states: data, 0-byte no-data marker, and corrupt.

  Scenario: Decodes scaled UTC ticks for EUR/USD
    Given a bi5 payload with EUR/USD records
      | ms_offset | ask_pts | bid_pts | ask_vol | bid_vol |
      | 86        | 111966  | 111963  | 4.39    | 0.75    |
      | 1086      | 111970  | 111968  | 1.0     | 2.0     |
    When I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC
    Then it yields 2 ticks
    And tick 0 has bid 1.11963 and ask 1.11966
    And tick 0 has timestamp 2020-01-02 14:00:00.086000 UTC
    And tick 0 has bid_volume 0.75 and ask_volume 4.39

  Scenario: USD/JPY uses its own increment, not the EUR/USD pip
    Given a bi5 payload with EUR/USD records
      | ms_offset | ask_pts | bid_pts | ask_vol | bid_vol |
      | 0         | 110120  | 110100  | 1.0     | 1.0     |
    When I decode it with the USD/JPY increment at hour 2020-01-02 14h UTC
    Then tick 0 has bid 110.10 and ask 110.12

  Scenario: An empty payload is no-data, not an error
    Given an empty bi5 payload
    When I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC
    Then it yields 0 ticks

  Scenario: A naive (non-UTC) hour start is rejected
    Given a bi5 payload with EUR/USD records
      | ms_offset | ask_pts | bid_pts | ask_vol | bid_vol |
      | 0         | 111966  | 111963  | 1.0     | 1.0     |
    When I decode it with the EUR/USD increment at a naive hour start
    Then it fails with ValueError mentioning "UTC"

  Scenario: A non-empty payload decompressing to empty is corrupt
    Given a bi5 payload that compresses an empty record stream
    When I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC
    Then it fails with DecodeError

  Scenario: Decoded quotes are ordered bid <= ask
    Given a bi5 payload with EUR/USD records
      | ms_offset | ask_pts | bid_pts | ask_vol | bid_vol |
      | 86        | 111966  | 111963  | 4.39    | 0.75    |
    When I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC
    Then tick 0 has bid not greater than ask

  Scenario: A corrupt payload raises a decode error
    Given a bi5 payload of non-LZMA bytes
    When I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC
    Then it fails with DecodeError

  Scenario: A truncated record stream raises a decode error
    Given a bi5 payload that compresses 25 bytes
    When I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC
    Then it fails with DecodeError
