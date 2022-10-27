#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_chip_info.h"
#include "hal/rtc_cntl_ll.h"
#include "unity.h"
#include "test_utils.h"
#include "esp_log.h"


TEST_CASE("normal_case1", "[normal_case]")
{
    esp_chip_info_t chip_info;
    esp_chip_info(&chip_info);
    ESP_LOGI("normal case1", "This is %s chip with %d CPU core(s), WiFi%s%s, ",
           CONFIG_IDF_TARGET,
           chip_info.cores,
           (chip_info.features & CHIP_FEATURE_BT) ? "/BT" : "",
           (chip_info.features & CHIP_FEATURE_BLE) ? "/BLE" : "");
    TEST_ASSERT(true);
}

TEST_CASE("normal_case2", "[normal_case][timeout=10]")
{
    ESP_LOGI("normal case2", "delay 100 ms");
    vTaskDelay(pdMS_TO_TICKS(3000));

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
    assert(false);
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
