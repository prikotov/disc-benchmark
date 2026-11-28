<?php
namespace App\Service;

class Scorer
{
    public function __construct(private QuestionsProvider $questions) {}

    public function score(array $ranked): array
    {
        $scores = ['d' => 0, 'i' => 0, 's' => 0, 'c' => 0];
        $byId = [];
        foreach ($this->questions->all() as $q) { $byId[$q['id']] = $q; }
        foreach ($ranked as $qid => $order) {
            $q = $byId[$qid] ?? null;
            if (!$q || count($order) !== 4) { continue; }
            foreach ($order as $pos => $itemIndex) {
                $item = $q['items'][$itemIndex] ?? null;
                if (!$item) continue;
                if ($pos === 0) $scores[$item['type']] += 1;
                if ($pos === 3) $scores[$item['type']] -= 1;
            }
        }
        return $scores;
    }
}
