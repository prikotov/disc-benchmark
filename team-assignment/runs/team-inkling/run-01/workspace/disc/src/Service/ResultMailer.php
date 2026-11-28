<?php
namespace App\Service;

use Symfony\Component\Mailer\Mailer;
use Symfony\Component\Mailer\Transport;
use Symfony\Component\Mime\Email;

class ResultMailer
{
    /** @return array{sent: bool, reason?: string} */
    public function send(string $to, array $scores, ?string $interpretation): array
    {
        $dsn = getenv('DISC_SMTP_DSN');
        if (!$dsn) {
            return ['sent' => false, 'reason' => 'Почта недоступна (DISC_SMTP_DSN не настроен)'];
        }
        try {
            $mailer = new Mailer(Transport::fromDsn($dsn));
            $email = (new Email())
                ->from('disc-test@ai-aid.pro')
                ->to($to)
                ->subject('Ваш результат теста DISC')
                ->html($this->renderHtml($scores, $interpretation));
            $mailer->send($email);
            return ['sent' => true];
        } catch (\Throwable $e) {
            return ['sent' => false, 'reason' => 'Письмо не отправлено: ' . $e->getMessage()];
        }
    }

    private function renderHtml(array $scores, ?string $interpretation): string
    {
        $items = '';
        foreach (['d' => 'D — Доминирование', 'i' => 'I — Влияние', 's' => 'S — Стабильность', 'c' => 'C — Сознательность'] as $k => $label) {
            $items .= "<li><strong>{$label}</strong>: {$scores[$k]}</li>";
        }
        $interp = nl2br(htmlspecialchars($interpretation ?? 'Интерпретация временно недоступна.', ENT_QUOTES, 'UTF-8'));
        return "<h1>Ваш результат теста DISC</h1><ul>{$items}</ul><h2>Интерпретация</h2><p>{$interp}</p>";
    }
}
