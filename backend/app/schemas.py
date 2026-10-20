from pydantic import BaseModel
from enum import StrEnum

class JapaneseTokenizedResponse(BaseModel):
    text : str
    dictionary_form : str
    katakana_reading : str
    start_idx : int
    end_idx : int
    part_of_speech: tuple[str,str,str,str,str,str]

class MajorPOS(StrEnum):
    NOUN = "名詞"
    PRONOUN = "代名詞"
    VERB = "動詞"
    ADJECTIVE = "形容詞"           # i-adjective
    ADJECTIVAL_NOUN = "形状詞"    # na-adjective stem
    ADVERB = "副詞"
    ADNOMINAL = "連体詞"          # Noun modifier, e.g. この
    CONJUNCTION = "接続詞"
    INTERJECTION = "感動詞"
    PARTICLE = "助詞"
    AUXILIARY_VERB = "助動詞"
    PREFIX = "接頭辞"
    SUFFIX = "接尾辞"
    SYMBOL = "記号"
    SUPPLEMENTARY_SYMBOL = "補助記号"  # Includes punctuation
    WHITESPACE = "空白"

class PartOfSpeech(BaseModel):
    major_pos: MajorPOS  # Your existing enum
    subcategory_1: str
    subcategory_2: str
    subcategory_3: str
    conjugation_type: str
    conjugation_form: str

    @classmethod
    def from_sudachi(
        cls,
        raw: tuple[str, str, str, str, str, str],
    ) -> "PartOfSpeech":
        return cls(
            major_pos=MajorPOS(raw[0]),
            subcategory_1=raw[1],
            subcategory_2=raw[2],
            subcategory_3=raw[3],
            conjugation_type=raw[4],
            conjugation_form=raw[5],
        )

class TokenGroup(BaseModel):
    text : str
    lookup_form : str
    start_idx : int
    end_idx : int
    tokens : list[JapaneseTokenizedResponse]


class ConjugationType(StrEnum):
    NOT_APPLICABLE = "*"
    UNINFLECTED = "無変化型"
    ADJECTIVE = "形容詞"

    # Irregular verbs
    KURU_IRREGULAR = "カ行変格"
    SURU_IRREGULAR = "サ行変格"

    # Godan verbs
    GODAN_KA = "五段-カ行"
    GODAN_GA = "五段-ガ行"
    GODAN_SA = "五段-サ行"
    GODAN_TA = "五段-タ行"
    GODAN_NA = "五段-ナ行"
    GODAN_BA = "五段-バ行"
    GODAN_MA = "五段-マ行"
    GODAN_RA = "五段-ラ行"
    GODAN_WA_A = "五段-ワア行"

    # Upper ichidan verbs
    UPPER_ICHIDAN_A = "上一段-ア行"
    UPPER_ICHIDAN_KA = "上一段-カ行"
    UPPER_ICHIDAN_GA = "上一段-ガ行"
    UPPER_ICHIDAN_ZA = "上一段-ザ行"
    UPPER_ICHIDAN_TA = "上一段-タ行"
    UPPER_ICHIDAN_NA = "上一段-ナ行"
    UPPER_ICHIDAN_HA = "上一段-ハ行"
    UPPER_ICHIDAN_BA = "上一段-バ行"
    UPPER_ICHIDAN_MA = "上一段-マ行"
    UPPER_ICHIDAN_RA = "上一段-ラ行"

    # Lower ichidan verbs
    LOWER_ICHIDAN_A = "下一段-ア行"
    LOWER_ICHIDAN_KA = "下一段-カ行"
    LOWER_ICHIDAN_GA = "下一段-ガ行"
    LOWER_ICHIDAN_SA = "下一段-サ行"
    LOWER_ICHIDAN_ZA = "下一段-ザ行"
    LOWER_ICHIDAN_TA = "下一段-タ行"
    LOWER_ICHIDAN_DA = "下一段-ダ行"
    LOWER_ICHIDAN_NA = "下一段-ナ行"
    LOWER_ICHIDAN_HA = "下一段-ハ行"
    LOWER_ICHIDAN_BA = "下一段-バ行"
    LOWER_ICHIDAN_MA = "下一段-マ行"
    LOWER_ICHIDAN_RA = "下一段-ラ行"

    # Auxiliaries
    AUX_JA = "助動詞-ジャ"
    AUX_TA = "助動詞-タ"
    AUX_TAI = "助動詞-タイ"
    AUX_DA = "助動詞-ダ"
    AUX_DESU = "助動詞-デス"
    AUX_DOSU = "助動詞-ドス"
    AUX_NAI = "助動詞-ナイ"
    AUX_NANDA = "助動詞-ナンダ"
    AUX_NU = "助動詞-ヌ"
    AUX_HEN = "助動詞-ヘン"
    AUX_MAI = "助動詞-マイ"
    AUX_MASU = "助動詞-マス"
    AUX_YA = "助動詞-ヤ"
    AUX_YASU = "助動詞-ヤス"
    AUX_RASHII = "助動詞-ラシイ"
    AUX_RERU = "助動詞-レル"

    # Classical irregular verbs
    CLASSICAL_KA_IRREGULAR = "文語カ行変格"
    CLASSICAL_SA_IRREGULAR = "文語サ行変格"
    CLASSICAL_NA_IRREGULAR = "文語ナ行変格"
    CLASSICAL_RA_IRREGULAR = "文語ラ行変格"

    # Classical upper ichidan verbs
    CLASSICAL_UPPER_ICHIDAN_NA = "文語上一段-ナ行"
    CLASSICAL_UPPER_ICHIDAN_MA = "文語上一段-マ行"
    CLASSICAL_UPPER_ICHIDAN_WA = "文語上一段-ワ行"

    # Classical upper nidan verbs
    CLASSICAL_UPPER_NIDAN_TA = "文語上二段-タ行"
    CLASSICAL_UPPER_NIDAN_DA = "文語上二段-ダ行"
    CLASSICAL_UPPER_NIDAN_HA = "文語上二段-ハ行"
    CLASSICAL_UPPER_NIDAN_BA = "文語上二段-バ行"
    CLASSICAL_UPPER_NIDAN_YA = "文語上二段-ヤ行"
    CLASSICAL_UPPER_NIDAN_RA = "文語上二段-ラ行"

    # Classical lower nidan verbs
    CLASSICAL_LOWER_NIDAN_A = "文語下二段-ア行"
    CLASSICAL_LOWER_NIDAN_KA = "文語下二段-カ行"
    CLASSICAL_LOWER_NIDAN_GA = "文語下二段-ガ行"
    CLASSICAL_LOWER_NIDAN_SA = "文語下二段-サ行"
    CLASSICAL_LOWER_NIDAN_ZA = "文語下二段-ザ行"
    CLASSICAL_LOWER_NIDAN_TA = "文語下二段-タ行"
    CLASSICAL_LOWER_NIDAN_DA = "文語下二段-ダ行"
    CLASSICAL_LOWER_NIDAN_NA = "文語下二段-ナ行"
    CLASSICAL_LOWER_NIDAN_HA = "文語下二段-ハ行"
    CLASSICAL_LOWER_NIDAN_BA = "文語下二段-バ行"
    CLASSICAL_LOWER_NIDAN_MA = "文語下二段-マ行"
    CLASSICAL_LOWER_NIDAN_YA = "文語下二段-ヤ行"
    CLASSICAL_LOWER_NIDAN_RA = "文語下二段-ラ行"
    CLASSICAL_LOWER_NIDAN_WA = "文語下二段-ワ行"

    # Classical yodan verbs
    CLASSICAL_YODAN_KA = "文語四段-カ行"
    CLASSICAL_YODAN_GA = "文語四段-ガ行"
    CLASSICAL_YODAN_SA = "文語四段-サ行"
    CLASSICAL_YODAN_TA = "文語四段-タ行"
    CLASSICAL_YODAN_HA = "文語四段-ハ行"
    CLASSICAL_YODAN_BA = "文語四段-バ行"
    CLASSICAL_YODAN_MA = "文語四段-マ行"
    CLASSICAL_YODAN_RA = "文語四段-ラ行"

    # Classical adjectives
    CLASSICAL_ADJECTIVE_KU = "文語形容詞-ク"
    CLASSICAL_ADJECTIVE_SHIKU = "文語形容詞-シク"

    # Classical auxiliaries
    CLASSICAL_AUX_KI = "文語助動詞-キ"
    CLASSICAL_AUX_KEMU = "文語助動詞-ケム"
    CLASSICAL_AUX_KERI = "文語助動詞-ケリ"
    CLASSICAL_AUX_GOTOSHI = "文語助動詞-ゴトシ"
    CLASSICAL_AUX_ZAMASU = "文語助動詞-ザマス"
    CLASSICAL_AUX_ZANSU = "文語助動詞-ザンス"
    CLASSICAL_AUX_JI = "文語助動詞-ジ"
    CLASSICAL_AUX_ZU = "文語助動詞-ズ"
    CLASSICAL_AUX_TARI_PERFECTIVE = "文語助動詞-タリ-完了"
    CLASSICAL_AUX_TARI_COPULA = "文語助動詞-タリ-断定"
    CLASSICAL_AUX_TSU = "文語助動詞-ツ"
    CLASSICAL_AUX_NARI_HEARSAY = "文語助動詞-ナリ-伝聞"
    CLASSICAL_AUX_NARI_COPULA = "文語助動詞-ナリ-断定"
    CLASSICAL_AUX_NU = "文語助動詞-ヌ"
    CLASSICAL_AUX_BESHI = "文語助動詞-ベシ"
    CLASSICAL_AUX_MAJI = "文語助動詞-マジ"
    CLASSICAL_AUX_MU = "文語助動詞-ム"
    CLASSICAL_AUX_RASHI = "文語助動詞-ラシ"
    CLASSICAL_AUX_RAMU = "文語助動詞-ラム"
    CLASSICAL_AUX_RI = "文語助動詞-リ"
    CLASSICAL_AUX_NSU = "文語助動詞-ンス"

class ConjugationForm(StrEnum):
    NOT_APPLICABLE = "*"

    # Stem
    STEM_GENERAL = "語幹-一般"
    STEM_SA = "語幹-サ"

    # Irrealis: 未然形
    IRREALIS_GENERAL = "未然形-一般"
    IRREALIS_SA = "未然形-サ"
    IRREALIS_SE = "未然形-セ"
    IRREALIS_NASAL = "未然形-撥音便"
    IRREALIS_SUPPLEMENTARY = "未然形-補助"

    # Continuative: 連用形
    CONTINUATIVE_GENERAL = "連用形-一般"
    CONTINUATIVE_GENERAL_OKURIGANA_OMITTED = "連用形-一般+送り仮名省略"
    CONTINUATIVE_I = "連用形-イ音便"
    CONTINUATIVE_I_OKURIGANA_OMITTED = "連用形-イ音便+送り仮名省略"
    CONTINUATIVE_U = "連用形-ウ音便"
    CONTINUATIVE_GEMINATE = "連用形-促音便"
    CONTINUATIVE_NASAL = "連用形-撥音便"
    CONTINUATIVE_KI_CONNECTION = "連用形-キ接続"
    CONTINUATIVE_TO = "連用形-ト"
    CONTINUATIVE_NI = "連用形-ニ"
    CONTINUATIVE_OMITTED = "連用形-省略"
    CONTINUATIVE_FUSED = "連用形-融合"
    CONTINUATIVE_SUPPLEMENTARY = "連用形-補助"

    # Terminal: 終止形
    TERMINAL_GENERAL = "終止形-一般"
    TERMINAL_U = "終止形-ウ音便"
    TERMINAL_GEMINATE = "終止形-促音便"
    TERMINAL_NASAL = "終止形-撥音便"
    TERMINAL_FUSED = "終止形-融合"
    TERMINAL_SUPPLEMENTARY = "終止形-補助"

    # Attributive: 連体形
    ATTRIBUTIVE_GENERAL = "連体形-一般"
    ATTRIBUTIVE_GENERAL_OKURIGANA_OMITTED = "連体形-一般+送り仮名省略"
    ATTRIBUTIVE_I = "連体形-イ音便"
    ATTRIBUTIVE_U = "連体形-ウ音便"
    ATTRIBUTIVE_NASAL = "連体形-撥音便"
    ATTRIBUTIVE_OMITTED = "連体形-省略"
    ATTRIBUTIVE_SUPPLEMENTARY = "連体形-補助"

    # Conditional: 仮定形
    CONDITIONAL_GENERAL = "仮定形-一般"
    CONDITIONAL_FUSED = "仮定形-融合"

    # Classical realis: 已然形
    REALIS_GENERAL = "已然形-一般"
    REALIS_SUPPLEMENTARY = "已然形-補助"

    IMPERATIVE = "命令形"
    VOLITIONAL_PRESUMPTIVE = "意志推量形"
    KU_NOMINALIZATION = "ク語法"