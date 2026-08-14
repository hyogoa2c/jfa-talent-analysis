from jfa_talent_analysis.gold_screen import screen_reason, screen_rows


def test_the_two_rows_the_reliability_subsample_caught_are_flagged():
    # W186 松澤彰: the note names the university the category skipped.
    assert screen_reason(
        "j_club_academy",
        "浦和レッズユース",
        "名古屋FC→浦和レッズユース",
        "高校年代は浦和レッズユース所属(3年次主将)。法政大学経由で2020年カターレ富山加入",
    )
    # W189 児玉剛: same shape, university between the academy and the first club.
    assert screen_reason(
        "j_club_academy",
        "京都パープルサンガユース",
        "2003-2005 京都パープルサンガユース",
        "2006-2009関西大学(2006年は特別指定選手として京都サンガF.C.に登録)を経てプロ入り",
    )


def test_a_university_run_high_school_is_not_a_later_stage():
    # W390 吉本一謙: 東海大学付属望星高校 is the school co-enrolled with the youth
    # side, and the rule already says the club side wins. Flagging it would send
    # every academy player at an affiliated high school to a second rater.
    assert not screen_reason(
        "j_club_academy",
        "FC東京U-18",
        "FC東京U-18(東海大学付属望星高)",
        "高校は東海大学付属望星高校と併記（クラブユースと同時在籍のためクラブ側を採用）",
    )
    assert not screen_reason(
        "high_school",
        "帝京大学可児高等学校",
        "岐阜ＶＡＭＯＳ－帝京大可児高－鹿島アントラーズ（2014～）",
        "",
    )


def test_a_school_renamed_after_its_university_is_not_a_later_stage():
    # W351 大西孝治: 香川西高等学校 is now 四国学院大学香川西高等学校. Blanking the
    # recorded institution out of the note took the 高 with it and left a bare
    # 大学 behind, which is how a correct row asked for a second rater.
    assert not screen_reason(
        "high_school",
        "香川西高等学校",
        "●　本校出身Ｊリーガー　９名　２００７年卒業｜大西孝治｜→徳島ヴォルティス→カマタマーレ讃岐（引退）",
        "2007年卒業。現・四国学院大学香川西高等学校",
    )


def test_the_recorded_institution_does_not_flag_itself():
    assert not screen_reason(
        "high_school",
        "東海大学第五高等学校",
        "高校は東海大学第五高等学校（略称は東海大五）を選択。",
        "",
    )


def test_an_abbreviated_university_still_flags():
    # Career lines write 桐蔭横浜大, not 桐蔭横浜大学.
    assert screen_reason(
        "j_club_academy",
        "横浜FCユース",
        "経歴=横浜FCユース-横浜FC-ギラヴァンツ北九州-横浜FC-桐蔭横浜大",
        "",
    )


def test_a_school_name_containing_大_is_not_an_abbreviated_university():
    # 大宮東 and 中京大中京 would both match a bare 大.
    assert not screen_reason(
        "high_school", "埼玉県立大宮東高等学校", "埼玉県立大宮東高校からプロへ", ""
    )
    assert not screen_reason(
        "high_school", "中京大中京高等学校", "名古屋グランパスJr.ユース/中京大中京高校", ""
    )


def test_only_categories_a_university_could_override_are_screened():
    quote = "経歴=ユース-法政大学-富山"
    assert screen_reason("j_club_academy", "", quote, "")
    assert screen_reason("high_school", "", quote, "")
    assert screen_reason("jfa_academy", "", quote, "")
    # Nothing sits above these, so a university mention says nothing about them.
    assert not screen_reason("university", "", quote, "")
    assert not screen_reason("other", "", quote, "")
    assert not screen_reason("unknown", "", quote, "")


def test_screen_rows_keeps_the_row_and_its_reason():
    rows = [
        {
            "worksheet_id": "W001",
            "gold_pathway_category": "j_club_academy",
            "gold_final_institution": "浦和レッズユース",
            "evidence_quote": "浦和レッズユース→法政大学→富山",
            "note": "",
        },
        {
            "worksheet_id": "W002",
            "gold_pathway_category": "university",
            "gold_final_institution": "法政大学",
            "evidence_quote": "法政大学→富山",
            "note": "",
        },
    ]
    flagged = screen_rows(rows)
    assert [row["worksheet_id"] for row, _ in flagged] == ["W001"]
    assert "大学" in flagged[0][1]
