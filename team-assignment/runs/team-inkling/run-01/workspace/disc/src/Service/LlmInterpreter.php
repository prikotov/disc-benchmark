<?php
namespace App\Service;

class LlmInterpreter
{
    public function interpret(array $scores): ?string
    {
        $base = getenv('DISC_LLM_BASE_URL');
        $model = getenv('DISC_LLM_MODEL');
        if (!$base || !$model) return null;
        $url = rtrim($base, '/') . '/chat/completions';

        $system = "Ты — эксперт по модели DISC. Отвечай только на русском языке, структурированно, без маркетингового тона.";
        $prompt = "Баллы по шкалам DISC (от -24 до +24, сумма = 0):\nD = {$scores['d']}\nI = {$scores['i']}\nS = {$scores['s']}\nC = {$scores['c']}\n\nНапиши индивидуальную интерпретацию профиля на русском: (1) общее описание профиля, (2) сильные стороны, (3) зоны роста, (4) рекомендации по взаимодействию с людьми других типов. Интерпретация должна отражать именно эти баллы. 5-8 абзацев, простой человеческий язык.";

        $body = json_encode([
            'model' => $model,
            'messages' => [
                ['role' => 'system', 'content' => $system],
                ['role' => 'user', 'content' => $prompt],
            ],
            'max_tokens' => 1200,
            'temperature' => 0.7,
        ]);

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_POSTFIELDS => $body,
            CURLOPT_TIMEOUT => 120,
        ]);
        $raw = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($raw === false || $code >= 400) return null;
        $data = json_decode($raw, true);
        $text = $data['choices'][0]['message']['content'] ?? null;
        if (!is_string($text) || trim($text) === '') return null;
        return trim($text);
    }
}
