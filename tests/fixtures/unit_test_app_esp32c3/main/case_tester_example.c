#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_chip_info.h"
#include "hal/rtc_cntl_ll.h"
#include "unity.h"
#include "test_utils.h"
#include "esp_log.h"


/*
The ideal test result of `run_all_single_board_cases(reset=False)` should be:
    normal_case_pass: pass
    normal_case_crash: fail (crash)
    normal_case_stuck: fail (infinite loop)
    normal_case_skip_when_not_reset: skip (since the previous case will hang forever)
    multiple_stages_test: skip (since the previous case will hang forever)

The ideal test result of `run_all_single_board_cases(reset=True)` should be:
    normal_case_pass: pass
    normal_case_crash: fail (crash)
    normal_case_stuck: fail (infinite loop)
    normal_case_skip_when_not_reset: pass
    multiple_stages_test: pass

multiple_devices_test: skip (when reset=False, since the previous case will hang forever)
multiple_devices_test: pass (when reset=True)
*/

TEST_CASE("normal_case_pass", "[normal_case]")
{
    esp_chip_info_t chip_info;
    esp_chip_info(&chip_info);
    ESP_LOGI("normal case pass", "This is %s chip with %d CPU core(s), WiFi%s%s, ",
           CONFIG_IDF_TARGET,
           chip_info.cores,
           (chip_info.features & CHIP_FEATURE_BT) ? "/BT" : "",
           (chip_info.features & CHIP_FEATURE_BLE) ? "/BLE" : "");

    TEST_ASSERT(true);
}

TEST_CASE("normal_case_crash", "[normal_case][timeout=10]")
{
    ESP_LOGI("normal case crash later", "delay 3s");
    vTaskDelay(pdMS_TO_TICKS(3000));

    // cause a crash
    volatile uint8_t *test = (uint8_t*)0x0;
    *test = 1;

    TEST_ASSERT(true);
}

TEST_CASE("normal_case_stuck", "[normal_case][timeout=10]")
{
    ESP_LOGI("normal case stuck", "infinite loop");
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    TEST_ASSERT(true);
}

TEST_CASE("normal_case_skip_when_not_reset", "[normal_case][timeout=10]")
{
    ESP_LOGI("normal case skip when not reset", "skip this case if not reset, since the previous case will hang forever");
    TEST_ASSERT(true);
}

void test_stage1(void)
{
    ESP_LOGI("multi_stage", "stage1: software restart");

    vTaskDelay(pdMS_TO_TICKS(100));
    esp_restart();
}

void test_stage2(void)
{
    ESP_LOGI("multi_stage", "stage2: assert fail");
    vTaskDelay(pdMS_TO_TICKS(100));
    assert(false);  // this one will cause a panic
}

void test_stage3(void)
{
    ESP_LOGI("multi_stage", "stage3: system reset");
    rtc_cntl_ll_reset_system();
}

void test_stage4(void)
{
    ESP_LOGI("multi_stage", "stage4: finish");
}

TEST_CASE_MULTIPLE_STAGES("multiple_stages_test", "[multi_stage]",
                          test_stage1, test_stage2, test_stage3, test_stage4);


void test_dev1(void)
{
    ESP_LOGI("multi_dev", "dev1 start");
    unity_send_signal("signal 1 from dev 1");
    unity_wait_for_signal("signal 2 from dev 2");
    unity_send_signal("signal 3 from dev 1");

    for (int i = 0; i < 10; i++) {
        unity_wait_for_signal("continuous signal");
    }
}

void test_dev2(void)
{
    ESP_LOGI("multi_dev", "dev2 start");
    unity_wait_for_signal("signal 1 from dev 1");
    unity_send_signal("signal 2 from dev 2");
    unity_wait_for_signal("signal 3 from dev 1");
    for (int i = 0; i < 10; i++) {
        unity_send_signal("continuous signal");
    }
}

TEST_CASE_MULTIPLE_DEVICES("multiple_devices_test", "[multi_dev][timeout=150]",
                           test_dev1, test_dev2);
