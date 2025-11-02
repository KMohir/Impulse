# ChatGPT Prompt Strukturasi

## 📋 To'liq Prompt

Bot audio dan olingan matnni (`stt_text`) quyidagi prompt bilan ChatGPT ga yuboradi:

### System Prompt:
```
Sen tajribali brend-strateg, professional ssenarist va motivatsion kontent prodyusersan. 
O'zbek tilida ajoyib video skriptlar yozasan. Har doim aniq strukturaga rioya qilasan va 
mijoz talablarini to'liq bajarasan. Faqat so'ralgan formatda javob berasan.
```

### User Prompt:
```
Sen — tajribali brend-strateg, ssenarist va motivatsion kontent prodyusersan. 
Yuqoridagi mijozning matni asosida 15 ta qisqa motivatsion video skript tayyorla. 
Har bir skript quyidagi qat'iy tuzilma bo'yicha bo'lsin va aniq ajratib yozilsin:

Sarlavha: (motivatsion, esda qoladigan nom — 3–6 so'z)
🎯 Hook: (birinchi 3 soniyada e'tibor tortadigan 1–2 jumla; kuchli boshlanish)
💡 Kontent g'oyasi: (video nimani o'rgatadi yoki qanday hissiyot uyg'otadi — 1–2 jumla)
🗣 Skript (100–120 so'z): (samimiy "sen" murojaatida, motivatsion va tabiiy ovozda; 
kamera qarshisida aytilishga mos; har bir skript 100–120 so'z orasida bo'lsin)

Qo'shimcha talablar:
- Til: o'zbekcha (lotin alifbosida)
- Ohang: motivatsion, ishonchli, tabiiy (sun'iy "trainer" ohangsiz)
- Format: javobda faqat 15 ta blok bo'lsin — hech qanday qo'shimcha izoh yoki tushuntirishsiz
- Har bir skript lichniy brend videoga mos (Reels / TikTok / Shorts: 40–60 soniya)
- Har bir hook qisqa, aniq va darhol e'tiborni tortadigan bo'lsin

Mana mijoz matni (audio dan olingan):

[STT_TEXT - audio dan olingan to'liq matn shu yerga qo'yiladi]
```

---

## 🎯 Kutilgan Javob Formati

ChatGPT quyidagi formatda javob berishi kerak:

```
Sarlavha: Maqsadingni Aniqla

🎯 Hook: Bilasanmi, ko'pchilik muvaffaqiyatsiz bo'lishining asosiy sababi nima? Ular aniq maqsad qo'ymaydi!

💡 Kontent g'oyasi: Bu video tomoshabinga o'z hayotida aniq maqsad belgilash va uni qog'ozga tushirish muhimligini tushuntiradi. Motivatsiya va amaliy maslahat beradi.

🗣 Skript (115 so'z): Sen kelajakda qanday o'zingni ko'rmoqchisan? Bu savolga javob topa olasanmi? Ko'pchilik odamlar kunlik hayotda kezib, aniq yo'nalishsiz yashaydi. Lekin muvaffaqiyat - bu tasodif emas, rejali ish natijasidir. Bugun senga bitta oddiy, lekin kuchli mashq tavsiya qilmoqchiman. Qog'oz ol va 5 yildan keyin o'zingni qayerda ko'rishni yoz. Aniq bo'l! "Boy bo'lmoqchiman" deb emas, "O'z biznesimni ochmoqchiman va oyiga X dollar daromad olmoqchiman" deb yoz. Maqsading qanchalik aniq bo'lsa, unga erishish yo'lingni topish shunchalik oson. Bugun boshlang!

---

Sarlavha: Sabr - Muvaffaqiyat Kaliti

🎯 Hook: Nega ba'zilar muvaffaqiyatga erishadiyu, ba'zilari esa yarmida to'xtaydi? Sabab juda oddiy.

💡 Kontent g'oyasi: Video sabr va izchillikning muvaffaqiyatdagi rolini tushuntiradi. Haqiqiy natija vaqt talab etishini anglatadi.

🗣 Skript (108 so'z): [... skript matni ...]

---

[... yana 13 ta skript shu formatda ...]
```

---

## 🔍 Muhim Nuqtalar

### STT Text Yuborilishi:
- ✅ Audio `combined_text` o'zgaruvchisida to'liq saqlanadi
- ✅ `_send_to_chatgpt(combined_text, user_prompt)` orqali yuboriladi
- ✅ ChatGPT mijoz audiosi asosida personallashtiradi

### Har Bir Skript:
- **Sarlavha**: 3-6 so'z, esda qoladigan
- **Hook**: 1-2 jumla, 3 soniyada e'tibor tortadi
- **Kontent g'oyasi**: 1-2 jumla, video mohiyati
- **Skript**: Aynan 100-120 so'z, "sen" shaklida

### Ohang va Stil:
- Motivatsion lekin tabiiy
- Sun'iy "trainer" yoki "motivator" ohangsiz
- Samimiy va ishonchli
- Kamera qarshisida to'g'ridan-to'g'ri gap sifatida

### Format:
- Faqat 15 ta blok
- Har bir blok `---` bilan ajratilgan
- Qo'shimcha izoh yoki kirish so'zi yo'q
- To'g'ridan-to'g'ri skriptlardan boshlaydi

---

## 📊 Texnik Parametrlar

```python
model: "gpt-4"
temperature: 0.7  # Kreativlik uchun
max_tokens: 4000  # 15 ta skript uchun yetarli
```

---

## 🧪 Test Qilish

Bot ishga tushirilganidan keyin:

1. Audio fayl yuboring
2. Bot STT natijasini ko'rsatadi
3. ChatGPT bilan ishlaydi (bir necha soniya)
4. 15 ta to'liq strukturalashgan skriptni olasiz

Har bir skript:
- ✅ Aniq strukturaga ega
- ✅ 100-120 so'z
- ✅ HeyGen uchun tayyor
- ✅ Reels/TikTok/Shorts ga mos

---

## 💡 Prompt O'zgartirish

Agar prompt o'zgartirmoqchi bo'lsangiz:

```python
# bot.py faylida 321-336 qatorlar:
user_prompt = (
    # Bu yerda prompt matnini o'zgartirasiz
)
```

Yoki system promptni:

```python
# bot.py faylida 197-202 qatorlar:
{
    "role": "system",
    "content": "Sizning yangi system prompt"
}
```
