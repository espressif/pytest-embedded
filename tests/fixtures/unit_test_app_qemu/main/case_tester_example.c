#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_chip_info.h"
#include "hal/rtc_cntl_ll.h"
#include "unity.h"
#include "test_utils.h"
#include "esp_log.h"


/*
The ideal test result of `run_all_single_board_cases` should be:
    normal_case_pass: pass
    normal_case_fail: fail


*/

TEST_CASE("normal_case_pass", "[normal_case]")
{
    TEST_ASSERT(true);
}

TEST_CASE("normal_case_fail", "[normal_case]")
{
    TEST_ASSERT(false);
}

void multi1_stage1(void)
{
    TEST_ASSERT_EQUAL(1, 2);
}

void multi1_stage2(void)
{
    TEST_ASSERT_EQUAL(1, 1);
}

void multi1_stage3(void)
{
    TEST_ASSERT_EQUAL(1, 1);
}

TEST_CASE_MULTIPLE_STAGES("multi_stage_fail_first", "[multi_stage]",
                          multi1_stage1, multi1_stage2, multi1_stage3);

void multi2_stage1(void)
{
    TEST_ASSERT(true);
}

void multi2_stage2(void)
{
    TEST_ASSERT(false);
}

void multi2_stage3(void)
{
    TEST_ASSERT_EQUAL(1, 1);
}

TEST_CASE_MULTIPLE_STAGES("multi_stage_fail_middle", "[multi_stage]",
                          multi2_stage1, multi2_stage2, multi2_stage3);

void multi3_stage1(void)
{
    TEST_ASSERT(true);
    TEST_ASSERT(true);
}

void multi3_stage2(void)
{
    TEST_ASSERT_EQUAL(1, 1);
}

void multi3_stage3(void)
{
    TEST_ASSERT(false);
}

TEST_CASE_MULTIPLE_STAGES("multi_stage_fail_last", "[multi_stage]",
                          multi3_stage1, multi3_stage2, multi3_stage3);

void multi4_stage1(void)
{
    TEST_ASSERT(true);
}

void multi4_stage2(void)
{
    int temp = 1;  // no assert
}

void multi4_stage3(void)
{
    TEST_ASSERT(true);
}

TEST_CASE_MULTIPLE_STAGES("multi_stage_pass", "[multi_stage]",
                          multi4_stage1, multi4_stage2, multi4_stage3);

TEST_CASE("normal_case_pass2", "[normal_case]")
{
    int temp = 1;  // no assert
}

TEST_CASE("normal_case_fail2", "[normal_case]")
{
    TEST_ASSERT(false);
}
