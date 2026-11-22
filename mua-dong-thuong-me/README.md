# Mùa đông thương mẹ — A Winter's Love for Mother

Thơ: Hồ Đình Bắc (1/2011) · *Kính tặng mẹ tám mươi lăm tuổi* · Giọng đọc: Hà Hồ

The manuscript has 20 lines with no stanza breaks. For the screen they are grouped four by four. The dedication appears on the title card.

## Lời thơ / Poem (transcribed exactly from the manuscript)

| Tiếng Việt | English subtitle |
|---|---|
| Nghe tin báo gió mùa đông bắc | When I hear the northeast winter wind is coming |
| Là lòng con thương mẹ lắm, mẹ ơi | My heart aches for you so, dear Mother |
| Dù đệm, chăn, áo ấm đã đủ rồi | Though you have quilts, blankets and warm coats |
| Nhưng giá buốt vẫn lùa trong lòng mẹ | The bitter cold still seeps into your heart |
| | |
| Ở nơi xa cầu mong cho mẹ khoẻ | From far away I pray that you stay well |
| Để đi chơi với bè bạn, xóm giềng | Well enough to visit friends and neighbours |
| Miếng trầu cay thấm nỗi sầu riêng. | Your bitter betel steeped in private sorrow. |
| Đời goá bụa nuôi con khi còn trẻ | Widowed young, you raised your children alone |
| | |
| Quy luật thời gian chẳng trừ ai cả. | Time's law spares no one at all. |
| Người cuối đời sức khoẻ có là bao | At life's end, how little strength remains |
| Lại gặp mùa đông gió rét gầm gào | And now comes winter, its cold winds howling |
| Tám lăm tuổi mẹ chịu làm sao được | At eighty-five, how can you bear it? |
| | |
| Nếu Bụt hiện cho con xin điều ước | If the Buddha of old tales granted me a wish |
| Thì mẹ ơi con ước cả mùa đông | Mother, I would wish for a whole winter |
| Không có rét về, không có mưa dông | With no cold coming, no storms, no rain |
| Toàn nắng ấm cho người già đỡ khổ. | Only warm sun to ease the hardship of the old. |
| | |
| Không ước được thì mẹ ơi sẽ cố | If wishes can't come true, Mother, hold on |
| Như ngày xưa mẹ đã vượt đói nghèo | As long ago you rose above hunger and want |
| Tết đến rồi, mùa xuân cũng về theo | Tết is here, and spring comes with it |
| Hết giá rét, nắng ấm về với mẹ. | The cold is gone, warm sun returns to you. |

## Kịch bản ghi âm (chỉ giọng)

`/` = ngừng ngắn · `//` = ngừng lâu (khoảng 2 giây)

```
Xin chào cả nhà, tôi là Hà Hồ. /
Mời mọi người cùng nghe bài thơ "Mùa đông thương mẹ" của bố tôi, nhà thơ Hồ Đình Bắc, kính tặng mẹ tám mươi lăm tuổi. //

Nghe tin báo gió mùa đông bắc /
Là lòng con thương mẹ lắm, mẹ ơi /
Dù đệm, chăn, áo ấm đã đủ rồi /
Nhưng giá buốt vẫn lùa trong lòng mẹ //

Ở nơi xa cầu mong cho mẹ khoẻ /
Để đi chơi với bè bạn, xóm giềng /
Miếng trầu cay thấm nỗi sầu riêng. /
Đời goá bụa nuôi con khi còn trẻ //

Quy luật thời gian chẳng trừ ai cả. /
Người cuối đời sức khoẻ có là bao /
Lại gặp mùa đông gió rét gầm gào /
Tám lăm tuổi mẹ chịu làm sao được //

Nếu Bụt hiện cho con xin điều ước /
Thì mẹ ơi con ước cả mùa đông /
Không có rét về, không có mưa dông /
Toàn nắng ấm cho người già đỡ khổ. //

Không ước được thì mẹ ơi sẽ cố /
Như ngày xưa mẹ đã vượt đói nghèo /
Tết đến rồi, mùa xuân cũng về theo /
Hết giá rét, nắng ấm về với mẹ. //
```

## Scene

The scene is more lifelike than the earlier poems, at Hà Hồ's request ("cho hình ảnh cảnh thật chút"). Everything is still drawn by code, so no outside images or photos are used.

- An overcast winter sky with layered clouds, and mountain ranges with smooth ridgelines, rock texture and atmospheric perspective. The nearest ridge is dotted with small trees.
- A narrow river that mirrors the hills.
- Winter rice fields after the harvest: plots divided by earth bunds and seen in perspective, some of them flooded.
- The mother's three-room tiled house (nhà ba gian), with a brick yard, a haystack and areca palms behind it (the trầu cau of stanza 2). She stands in her doorway from stanza 1 onward. Kitchen smoke bends in the wind.
- A bare old tree on the left, and bamboo on the right.
- The mood follows the poem: cold grey winter, then a howling storm with slanted rain and lamplight in the windows (stanza 3), then a golden glow for the wish (stanza 4). In stanza 5 the scene turns to spring for Tết: the sun comes out, the fields turn green, peach blossoms open and petals fall.

## Render

`timing.json` holds the line start times taken from Hà Hồ's recording, found with pause detection and checked against the 5 × 4 line structure. The recording is not in the repo. It is trimmed to [1.3, 93.5] s and starts at video t = 0.8 s.

```bash
python3 music.py music.wav
ffmpeg -i voice.m4a -af "atrim=1.3:93.5,asetpts=N/SR/TB,afade=t=in:d=0.2,highpass=f=80,afftdn=nf=-30,acompressor=threshold=-24dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11,adelay=800:all=1,aresample=44100,aformat=channel_layouts=stereo" voice_clean.wav
for r in "0 25.34 p1" "25.34 50.68 p2" "50.68 76.02 p3" "76.02 101.36 p4"; do set -- $r; python3 silk.py full $1 $2 $3.mp4 & done; wait
printf "file '%s'\n" p1.mp4 p2.mp4 p3.mp4 p4.mp4 > list.txt
ffmpeg -f concat -i list.txt -i voice_clean.wav -i music.wav -filter_complex "[1:a][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -movflags +faststart mua-dong-thuong-me.mp4
```
