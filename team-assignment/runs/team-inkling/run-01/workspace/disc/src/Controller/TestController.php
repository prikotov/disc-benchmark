<?php

namespace App\Controller;

use App\Service\QuestionsProvider;
use App\Service\Scorer;
use App\Service\LlmInterpreter;
use App\Service\ResultMailer;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class TestController extends AbstractController
{
    public function __construct(
        private QuestionsProvider $questions,
        private Scorer $scorer,
        private LlmInterpreter $llm,
        private ResultMailer $mailer,
    ) {}

    #[Route('/', name: 'home')]
    public function home(): Response
    {
        return $this->render('home.html.twig');
    }

    #[Route('/test', name: 'test')]
    public function test(): Response
    {
        $steps = $this->questions->steps();
        // Strip type info before sending to client
        $public = [];
        foreach ($steps as $stepIndex => $qs) {
            $public[$stepIndex] = [];
            foreach ($qs as $q) {
                $public[$stepIndex][] = [
                    'id' => $q['id'],
                    'items' => array_map(fn($it) => ['text' => $it['text']], $q['items']),
                ];
            }
        }
        return $this->render('test.html.twig', ['steps' => $public]);
    }

    #[Route('/test/finish', name: 'test_finish', methods: ['POST'])]
    public function finish(Request $request): Response
    {
        $data = json_decode($request->getContent(), true) ?? [];
        $answers = $data['answers'] ?? [];
        $email = trim((string)($data['email'] ?? ''));

        // validate
        $valid = true;
        $byId = [];
        foreach ($this->questions->all() as $q) { $byId[$q['id']] = $q; }
        if (count($answers) !== 24) $valid = false;
        foreach ($answers as $qid => $order) {
            $q = $byId[$qid] ?? null;
            if (!$q) { $valid = false; continue; }
            if (!is_array($order) || count($order) !== 4) { $valid = false; continue; }
            sort($order);
            if ($order !== [0, 1, 2, 3]) { $valid = false; }
        }
        $validEmail = filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
        if (!$valid) {
            return $this->json(['ok' => false, 'error' => 'Неполные ответы'], Response::HTTP_BAD_REQUEST);
        }
        if (!$validEmail) {
            return $this->json(['ok' => false, 'error' => 'Некорректный email'], Response::HTTP_BAD_REQUEST);
        }

        $scores = $this->scorer->score($answers);
        $interpretation = $this->llm->interpret($scores);
        $mail = $this->mailer->send($email, $scores, $interpretation);

        return $this->json([
            'ok' => true,
            'scores' => $scores,
            'interpretation' => $interpretation,
            'interpretation_unavailable' => $interpretation === null,
            'mail_sent' => $mail['sent'],
            'mail_reason' => $mail['reason'] ?? null,
            'email' => $email,
        ]);
    }
}
