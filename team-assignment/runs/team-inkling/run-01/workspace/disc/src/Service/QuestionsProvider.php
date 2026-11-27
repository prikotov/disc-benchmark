<?php
namespace App\Service;

class QuestionsProvider
{
    public function all(): array
    {
        $json = file_get_contents(__DIR__.'/../Data/questions.json');
        return json_decode($json, true)['questions'];
    }

    public function steps(): array
    {
        $steps = [];
        foreach ($this->all() as $q) {
            $steps[$q['step']][] = $q;
        }
        ksort($steps);
        return $steps;
    }
}
