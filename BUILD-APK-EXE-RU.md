# Сборка PastMetki в APK и EXE через GitHub

В репозитории уже добавлены GitHub Actions:
- `.github/workflows/build-android.yml` — собирает Android debug APK;
- `.github/workflows/build-windows.yml` — собирает Windows установщик `.exe` и portable `.exe`.

## Как получить файлы
1. Создай репозиторий на GitHub и загрузи в него всё содержимое этой папки.
2. Открой вкладку **Actions**.
3. Запусти **Build Android APK** и **Build Windows EXE** кнопкой **Run workflow** (или дождись автоматической сборки после push в `main`/`master`).
4. Открой завершённый запуск workflow и скачай ZIP из раздела **Artifacts**:
   - `PastMetki-Android-APK` — внутри `app-debug.apk`;
   - `PastMetki-Windows-EXE` — установщик и portable-версия `.exe`.

## Перед сборкой
1. В `config.js` укажи `SUPABASE_URL` и публичный `SUPABASE_ANON_KEY` своего проекта.
2. В Supabase выполни `supabase.sql` и настрой Authentication так, как описано в `README.md`.
3. Не добавляй в проект `service_role` key или другие секретные ключи. Публичный anon/publishable key предназначен для клиентского приложения; безопасность обеспечивается RLS.

## Важно
- APK собирается как **debug APK** для тестирования и ручной установки. Для публикации в Google Play нужен release APK/AAB, подпись и настройка keystore.
- Windows EXE собирается на Windows runner GitHub Actions. Это не подписанный цифровым сертификатом установщик, поэтому Windows SmartScreen может показать предупреждение.
- GitHub Actions сохраняет артефакты ограниченное время согласно настройкам репозитория. Для постоянной раздачи можно прикрепить файлы к GitHub Release.
- Для первого запуска Android workflow создаёт папку `android` автоматически; она не хранится в исходном ZIP.


## Важно: правильная загрузка в GitHub

В корне репозитория должны сразу лежать `package.json`, `index.html`, `app.js`, `config.js` и папка `.github/workflows`. Не загружайте дополнительную вложенную папку `PastMetki` целиком: откройте её и загрузите именно всё её содержимое в корень репозитория. Иначе GitHub Actions не найдёт `package.json`.

В workflow отключен npm cache, чтобы `setup-node` не требовал заранее созданный `package-lock.json`. Команда `npm install` сама установит зависимости.
