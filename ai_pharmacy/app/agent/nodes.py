from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.agent.state import AgentState
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.tools.compare_products import compare_products_tool, find_cheapest_tool
from app.tools.filter_products import filter_products_tool
from app.tools.product_details import product_details_tool
from app.tools.product_search import search_products_tool
from app.tools.web_search import web_search_tool

TOOLS = [
    search_products_tool,
    compare_products_tool,
    find_cheapest_tool,
    filter_products_tool,
    product_details_tool,
    web_search_tool,
]

SYSTEM_PROMPT = SystemMessage(
    content=(
        "Siz AI Pharmacy Price Comparison Agent — O'zbekistondagi internet "
        "dorixonalari va vitamin do'konlaridan mahsulot narxlarini qidiruvchi va "
        "taqqoslovchi yordamchisiz.\n\n"
        "QAT'IY QOIDALAR:\n"
        "1. Mahsulot nomi, brendi yoki narxini HECH QACHON o'zingiz o'ylab topmang. "
        "Har doim mos tool'ni chaqirib, faqat tool natijasidagi haqiqiy ma'lumotdan "
        "foydalaning.\n"
        "2. Siz tibbiy maslahat beruvchi emassiz: kasallikka tashxis qo'ymang, "
        "davolash usulini tavsiya qilmang, retsept bo'yicha dori tavsiya qilmang va "
        "qaysi dori/vitaminni qabul qilish kerakligini hal qilmang.\n"
        "3. Sizning vazifangiz — foydalanuvchiga xarid qilish qarorini (narx, brend, "
        "do'kon solishtirish) qabul qilishda yordam berish, tibbiy qaror qabul qilish "
        "emas.\n"
        "4. Agar foydalanuvchi tibbiy maslahat so'rasa, buni qila olmasligingizni "
        "ayting va shifokorga murojaat qilishni tavsiya qiling, so'ng faqat narx/"
        "mahsulot qidirishda yordam berishga qayting.\n"
        "5. Natijalarni aniq va qulay ko'rinishda (jadval, ro'yxat) taqdim eting: "
        "mahsulot nomi, brend, narx, do'kon, mavjudligi.\n"
        "6. Agar hech narsa topilmasa yoki xatolik yuz bersa, buni foydalanuvchiga "
        "tushunarli tarzda tushuntiring va nima qilish mumkinligini tavsiya qiling.\n"
        "7. Suhbat davomida oldingi kontekstni (masalan, oldin qidirilgan mahsulot yoki "
        "qo'llanilgan filtrlar) eslab qoling va keyingi so'rovlarda undan foydalaning.\n"
        "8. web_search_tool faqat tibbiy bo'lmagan qo'shimcha ma'lumot uchun (masalan, "
        "ishlab chiqaruvchi mamlakati, notanish brend haqida ma'lumot): narx yoki "
        "mahsulot mavjudligini HECH QACHON web_search_tool natijasidan olmang — narx/"
        "mavjudlik faqat dorixona qidiruv tool'laridan (search_products_tool va h.k.) "
        "kelishi shart."
    )
)

_llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
llm_with_tools = _llm.bind_tools(TOOLS)
# Forced on the first step of every turn so the small local model cannot skip
# straight to a free-form (possibly fabricated) answer for a product query.
llm_forced_tool = _llm.bind_tools(TOOLS, tool_choice="any")


def call_model(state: AgentState) -> dict:
    messages = [SYSTEM_PROMPT] + state["messages"]

    is_turn_start = isinstance(state["messages"][-1], HumanMessage)
    model = llm_forced_tool if is_turn_start else llm_with_tools

    response = model.invoke(messages)
    return {"messages": [response]}
