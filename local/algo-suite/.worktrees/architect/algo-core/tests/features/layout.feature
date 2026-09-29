Feature: Storage layout and config conventions
  The suite resolves every path from one data root and follows the conf/
  convention, with environment variables overriding the defaults.

  Scenario: data_root defaults to the workspace data directory
    Given no ALGO_DATA_ROOT is set
    When I resolve the data root
    Then the data root is named "data" inside the algo-suite workspace

  Scenario: ALGO_DATA_ROOT overrides the data root
    Given ALGO_DATA_ROOT is set to "/mnt/nas/tcc"
    When I resolve the data root
    Then the data root path is "/mnt/nas/tcc"

  Scenario: config paths follow the conf/ convention
    Given no ALGO_CONF_DIR is set
    When I resolve the config paths
    Then the conf dir is named "conf"
    And the global config file is named "algo.yaml"
    And the download tool config file is named "download.yaml"

  Scenario: ALGO_CONF_DIR relocates the conf directory
    Given ALGO_CONF_DIR is set to "/conf"
    When I resolve the config paths
    Then the conf dir path is "/conf"
    And the global config path is "/conf/algo.yaml"
