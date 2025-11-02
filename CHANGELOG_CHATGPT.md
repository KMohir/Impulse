# Changelog - ChatGPT Integration v2.0

## 📅 02.11.2025 - Prompt Strukturasi Yangilandi

### ✨ Yangi Xususiyatlar

#### 1. **Batafsil Prompt Strukturasi**
- Har bir video skript uchun aniq format
- 4 ta majburiy element: Sarlavha, Hook, Kontent g'oyasi, Skript
- Emoji bilan belgilangan strukturalar

#### 2. **Professional System Prompt**
```
Sen tajribali brend-strateg, professional ssenarist va motivatsion kontent prodyusersan.
```
- Yanada professional rol ta'rifi
- O'zbek tiliga moslashtirilgan
- Aniq formatda javob berish talabi

#### 3. **Detailed User Prompt**
Yangi prompt quyidagilarni o'z ichiga oladi:
- Aniq tuzilma talabi (Sarlavha, Hook, Kontent g'oyasi, Skript)
- Har bir element uchun batafsil ko'rsatmalar
- 100-120 so'z chegarasi
- Reels/TikTok/Shorts uchun optimallashtirilgan

---

## 🔧 O'zgarishlar

### `bot.py`

#### System Prompt (197-202 qatorlar):
```python
{
    "role": "system", 
    "content": "Sen tajribali brend-strateg, professional ssenarist va motivatsion kontent prodyusersan. "
               "O'zbek tilida ajoyib video skriptlar yozasan. Har doim aniq strukturaga rioya qilasan va "
               "mijoz talablarini to'liq bajarasan. Faqat so'ralgan formatda javob berasan."
}
```

#### User Prompt (321-336 qatorlar):
```python
user_prompt = (
    "Sen — tajribali brend-strateg, ssenarist va motivatsion kontent prodyusersan. "
    "Yuqoridagi mijozning matni asosida 15 ta qisqa motivatsion video skript tayyorla. "
    "Har bir skript quyidagi qat'iy tuzilma bo'yicha bo'lsin va aniq ajratib yozilsin:\n\n"
    "Sarlavha: (motivatsion, esda qoladigan nom — 3–6 so'z)\n"
    "🎯 Hook: (birinchi 3 soniyada e'tibor tortadigan 1–2 jumla; kuchli boshlanish)\n"
    "💡 Kontent g'oyasi: (video nimani o'rgatadi yoki qanday hissiyot uyg'otadi — 1–2 jumla)\n"
    "🗣 Skript (100–120 so'z): (samimiy \"sen\" murojaatida, motivatsion va tabiiy ovozda; "
    "kamera qarshisida aytilishga mos; har bir skript 100–120 so'z orasida bo'lsin)\n\n"
    "Qo'shimcha talablar:\n"
    "- Til: o'zbekcha (lotin alifbosida)\n"
    "- Ohang: motivatsion, ishonchli, tabiiy (sun'iy \"trainer\" ohangsiz)\n"
    "- Format: javobda faqat 15 ta blok bo'lsin — hech qanday qo'shimcha izoh yoki tushuntirishsiz\n"
    "- Har bir skript lichniy brend videoga mos (Reels / TikTok / Shorts: 40–60 soniya)\n"
    "- Har bir hook qisqa, aniq va darhol e'tiborni tortadigan bo'lsin"
)
```

### `SETUP_CHATGPT.md`
- Prompt strukturasi yangilandi
- Misol dialog yangilandi
- Batafsil format ko'rsatildi

---

## 📁 Yangi Fayllar

1. **`PROMPT_STRUCTURE.md`**
   - To'liq prompt strukturasi
   - Kutilgan javob formati
   - Texnik parametrlar
   - Test qilish yo'riqnomasi

2. **`CHANGELOG_CHATGPT.md`**
   - O'zgarishlar tarixi
   - Versiya ma'lumotlari

---

## 🎯 Natija

### Audio -> STT -> ChatGPT -> 15 ta Skript

Har bir skript quyidagi formatda:

```
Sarlavha: [3-6 so'z]

🎯 Hook: [1-2 jumla, kuchli boshlanish]

💡 Kontent g'oyasi: [1-2 jumla, video mohiyati]

🗣 Skript (100–120 so'z): [Motivatsion, samimiy matn]

---
```

---

## ✅ STT Text Yuborilishi Tasdiqlandi

```python
# bot.py, 338-qator:
chatgpt_response = await _send_to_chatgpt(combined_text, user_prompt)

# _send_to_chatgpt funksiyasi, 203-qator:
{"role": "user", "content": f"{user_prompt}\n\nMana mijoz matni (audio dan olingan):\n\n{stt_text}"}
```

**To'liq audio transcript ChatGPT ga yuboriladi** ✅

---

## 🔍 Tekshirish

### STT Text Path:
1. Audio yuklanadi → `handle_audio_message()`
2. STT orqali matnга aylanadi → `_post_to_stt()`
3. `combined_text` ga yig'iladi
4. FSM da saqlanadi → `await state.update_data(stt_text=combined_text)`
5. ChatGPT ga yuboriladi → `await _send_to_chatgpt(combined_text, user_prompt)`

### Prompt Path:
1. `user_prompt` yaratiladi (321-336 qatorlar)
2. `_send_to_chatgpt()` ga yuboriladi
3. OpenAI API ga request yuboriladi
4. GPT-4 javob qaytaradi
5. Foydalanuvchiga yuboriladi

---

## 🚀 Ishlatish

```bash
# Bot ishga tushirish
cd /home/mohirbek/Projects/Impulse
python bot.py

# Audio yuborish
# → STT natijasini olish
# → ChatGPT 15 ta skript yaratadi
# → Strukturalashgan natijalarni olish
```

---

## 📋 Version Info

- **Version**: 2.0
- **Date**: 02.11.2025
- **Changes**: Prompt strukturasi to'liq yangilandi
- **Author**: Mohirbek
- **Status**: ✅ Production Ready

---

## 🔗 Related Files

- `bot.py` - Asosiy bot kodi
- `config.py` - API keys
- `SETUP_CHATGPT.md` - Setup yo'riqnomasi
- `PROMPT_STRUCTURE.md` - Prompt strukturasi
- `.env` - Environment variables

---

## 💡 Keyingi Versiyalar Uchun G'oyalar

- [ ] Database ga skriptlarni saqlash
- [ ] Foydalanuvchi feedback qo'shish
- [ ] Skriptlarni export qilish (PDF/DOCX)
- [ ] Video generator integration (HeyGen API)
- [ ] Multi-language support
- [ ] Custom prompt templates
