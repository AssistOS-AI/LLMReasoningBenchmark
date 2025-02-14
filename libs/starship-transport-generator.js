export function generateRandomConfig(numSpecies, numIndividualsPerSpecies, numRelationships, starshipCapacity) {
    // Small helper to generate species
    function randomName() {
        const chars = "abcdefghijklmnopqrstuvwxyz";
        let result = "";
        for (let i = 0; i < 5; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    // Build species array
    const species = [];
    for (let i = 0; i < numSpecies; i++) {
        species.push({
            name: randomName(),
            count: numIndividualsPerSpecies
        });
    }

    // Build relationships
    const relationships = [];
    const usedPairs = new Set();
    let attempts = 0;
    while (relationships.length < numRelationships && attempts < 1000) {
        attempts++;
        const predIdx = Math.floor(Math.random() * numSpecies);
        let preyIdx = Math.floor(Math.random() * numSpecies);
        while (preyIdx === predIdx) {
            preyIdx = Math.floor(Math.random() * numSpecies);
        }
        const key = `${predIdx}-${preyIdx}`;
        if (!usedPairs.has(key)) {
            usedPairs.add(key);
            relationships.push({
                predator: species[predIdx].name,
                prey: species[preyIdx].name,
            });
        }
    }

    // Final config object
    return {
        species,
        relationships,
        starshipCapacity
    };
}

/**
 * Generates all allowed "moves" for a starship carrying up to `capacity`
 * across `n` species.
 */
function generateAllowedMoves(n, capacity) {
    const moves = [];

    function helper(current, index) {
        if (index === n) {
            const total = current.reduce((a, b) => a + b, 0);
            if (total >= 1 && total <= capacity) {
                moves.push([...current]);
            }
            return;
        }
        for (let i = 0; i <= capacity; i++) {
            current.push(i);
            helper(current, index + 1);
            current.pop();
        }
    }

    helper([], 0);
    return moves;
}

/**
 * Generates the Prolog code for the generalized transport puzzle.
 *
 * Each solution is a list of:
 *   move(MoveList, state(OldCounts,OldSide), state(NewCounts,NewSide))
 * so we can reconstruct the crossing details in JavaScript.
 */
export function generatePrologCode(config) {
    const species = config.species;
    const relationships = config.relationships || [];
    const starshipCapacity = config.starshipCapacity || 2;
    const n = species.length;
    const speciesNames = species.map((s) => s.name);
    const initCounts = species.map((s) => s.count);
    const zeros = Array(n).fill(0);

    // 1) Allowed moves
    const allowedMoves = generateAllowedMoves(n, starshipCapacity);
    const movesCode = allowedMoves
        .map((move) => `move([${move.join(",")}]).`)
        .join("\n");

    // 2) Facts for initial/final states
    const initCountsFact = `init_counts([${initCounts.join(",")}]).`;
    const initialStateFact = `initial_state(state([${initCounts.join(",")}],start)).`;
    const finalStateFact = `final_state(state([${zeros.join(",")}],target)).`;

    // 3) Safety predicate
    //    - If no relationships, safe/1 is trivially true.
    //    - Otherwise, ensure prey are not outnumbered by predators on either side.
    let safePredicate = "";
    if (relationships.length === 0) {
        safePredicate = "safe(_).";
    } else {
        safePredicate = "safe(state(Counts,_)) :- \n";
        relationships.forEach((rel, idx) => {
            const predatorIndex = speciesNames.indexOf(rel.predator);
            const preyIndex = speciesNames.indexOf(rel.prey);

            safePredicate += `    nth0(${predatorIndex}, Counts, PredCount${idx}),\n`;
            safePredicate += `    nth0(${preyIndex}, Counts, PreyCount${idx}),\n`;
            safePredicate += `    (PreyCount${idx} =:= 0 ; PreyCount${idx} >= PredCount${idx}),\n`;
            safePredicate += `    init_counts(Init),\n`;
            safePredicate += `    nth0(${predatorIndex}, Init, InitPred${idx}),\n`;
            safePredicate += `    nth0(${preyIndex}, Init, InitPrey${idx}),\n`;
            safePredicate += `    TargetPred${idx} is InitPred${idx} - PredCount${idx},\n`;
            safePredicate += `    TargetPrey${idx} is InitPrey${idx} - PreyCount${idx},\n`;
            safePredicate += `    (TargetPrey${idx} =:= 0 ; TargetPrey${idx} >= TargetPred${idx})${
                idx === relationships.length - 1 ? "." : ","
            }\n`;
        });
    }

    // 4) Supporting list predicates
    const basePredicates = `
% List manipulation predicates
nth0(0, [H|_], H) :- !.
nth0(N, [_|T], X) :-
    N > 0,
    N1 is N - 1,
    nth0(N1, T, X).

member(X, [X|_]).
member(X, [_|T]) :- member(X, T).

% Move application
apply_move_subtract([], [], []).
apply_move_subtract([X|Xs], [Y|Ys], [Z|Zs]) :-
    Z is X - Y,
    Z >= 0,
    apply_move_subtract(Xs, Ys, Zs).

apply_move_add([], [], [], []).
apply_move_add([X|Xs], [I|Is], [Y|Ys], [Z|Zs]) :-
    Available is I - X,
    Y =< Available,
    Z is X + Y,
    apply_move_add(Xs, Is, Ys, Zs).

% not_member
not_member(_, []).
not_member(X, [H|T]) :-
    X \\= H,
    not_member(X, T).
`;

    // 5) Enhanced transitions that unify the Move used, so the solution list can show it.
    const transitionRules = `
% We store the Move used in the solution as well: move(Move, OldState, NewState).

transition_with_move(state(Counts,start), Move, state(NewCounts,target)) :-
    move(Move),
    apply_move_subtract(Counts, Move, NewCounts),
    safe(state(NewCounts,target)).

transition_with_move(state(Counts,target), Move, state(NewCounts,start)) :-
    move(Move),
    init_counts(Init),
    apply_move_add(Counts, Init, Move, NewCounts),
    safe(state(NewCounts,start)).
`;

    // 6) Path finding that includes the Move in the solution:
    const pathPredicates = `
% A solution is a list of move(Move,OldState,NewState).

path(State, _, []) :-
    final_state(State).

path(State, Visited, [move(Move,State,NextState)|Moves]) :-
    transition_with_move(State, Move, NextState),
    not_member(NextState, Visited),
    path(NextState, [NextState|Visited], Moves).

solve_solution(Solution) :-
    initial_state(Initial),
    path(Initial, [Initial], Solution).
`;

    const checkSolutionPredicates = `
% check_solution(+Steps, +CurrentState)
% Steps is a list of step(MoveList, Direction).
% Direction is either leftToRight or rightToLeft.
% It succeeds iff we can apply all steps in order and end in final_state.

check_solution([], State) :-
    final_state(State).   % All steps used up, must be at final_state

check_solution([step(Move, leftToRight)|Rest], state(Counts, start)) :-
    transition_with_move(state(Counts, start), Move, state(NewCounts, target)),
    check_solution(Rest, state(NewCounts, target)).

check_solution([step(Move, rightToLeft)|Rest], state(Counts, target)) :-
    transition_with_move(state(Counts, target), Move, state(NewCounts, start)),
    check_solution(Rest, state(NewCounts, start)).
`;

    // Concatenate it all
    return [
        movesCode,
        initCountsFact,
        initialStateFact,
        finalStateFact,
        safePredicate,
        basePredicates,
        transitionRules,
        pathPredicates,
        checkSolutionPredicates
    ].join("\n\n");
}

/**
 * Logs a natural language description (to the console) of the puzzle.
 */

export function generateProblemDescription(config) {
    const starshipCapacity = config.starshipCapacity || 2;
    let problemDescription = "Solve the following transport puzzle:\n\n";
    problemDescription += `A shuttle with capacity ${starshipCapacity} must transport a group of species from the start to the target bank.\n`;
    config.species.forEach((s) =>
        problemDescription += `  - ${s.name}: ${s.count} individual(s)\n`
    );

    if (config.relationships && config.relationships.length > 0) {
        config.relationships.forEach((rel) =>
            problemDescription += `  * On either bank, if ${rel.prey} are present, they must not be outnumbered by ${rel.predator}.\n`
        );
    } else {
        problemDescription += "There are no safety constraints among species.\n";
        console.log("There are no safety constraints among species.");
    }

    problemDescription += `CRITICAL RESPONSE FORMATTING REQUIREMENTS:
        1. Your response MUST start with an opening square bracket [
        2. Your response MUST end with a closing square bracket ]
        3. Use double quotes for all strings
        4. Do not include any text, comments, or explanations outside the array structure
        5. Follow this exact structure:
        ["n1 speciesName1, n2 speciesName2 cross left -> right", ...]`;

    return problemDescription;
}

/**
 * Convert Prolog "side" atoms to the user-friendly string "left" or "right".
 */
function sideToText(sideAtom) {
    return sideAtom.id === "start" ? "left" : "right";
}

/**
 * Convert a single "move(MoveList, state(OldCounts,OldSide), state(NewCounts,NewSide))"
 * into a textual description like "2 zargons cross left -> right".
 *
 * If multiple species are moved, it might say "2 zargons, 1 martian cross left -> right".
 */
function moveToSentence(moveTerm, species) {
    // The moveTerm structure in Tau Prolog's internal representation:
    // moveTerm.id === "move"
    // moveTerm.args = [ MoveList, OldState, NewState ]
    //
    // MoveList is a prolog list, e.g. .(2, .(0, .(1, []))) for [2,0,1]
    // OldState = state(OldCounts,OldSide)
    // NewState = state(NewCounts,NewSide)
    //
    const [moveList, oldState, newState] = moveTerm.args;

    // Extract side from oldState: state(Counts, Side)
    // oldState.args = [ OldCountsList, OldSideAtom ]
    const oldSideAtom = oldState.args[1];
    const newSideAtom = newState.args[1];

    const direction = sideToText(oldSideAtom) + " -> " + sideToText(newSideAtom);

    // Convert Prolog list of integers to a JS array
    const amounts = prologListToArray(moveList);

    // Build a list of "X speciesName(s)"
    const segments = [];
    for (let i = 0; i < amounts.length; i++) {
        const count = amounts[i];
        if (count > 0) {
            const spName = species[i].name;
            segments.push(`${count} ${spName}`);
        }
    }

    // Combine them into a single phrase
    // e.g. "2 zargons, 1 martian"
    const crossingWhat = segments.join(", ");
    const verb = "cross";

    return `${crossingWhat} ${verb} ${direction}`;
}

/**
 * Convert a Prolog list structure to a JS array of numbers (integers).
 * Example of a prolog list: .(2, .(0, .(1, []))) => [2,0,1]
 */
function prologListToArray(listTerm) {
    const arr = [];
    let current = listTerm;
    while (current.indicator === "./2") {
        // head is current.args[0], tail is current.args[1]
        const head = current.args[0];
        arr.push(head.value); // head.value is the integer
        current = current.args[1];
    }
    return arr;
}

/**
 * Convert an entire Prolog solution (which is a list of move(...) terms)
 * into an array of human-readable steps:
 *   [
 *     "2 zargons cross left -> right",
 *     "1 warg crosses right -> left",
 *     ...
 *   ]
 */
function solutionToHumanReadableList(solutionTerm, species) {
    // The solutionTerm is a Prolog list of move/3 terms.
    // We'll iterate until we reach an empty list.
    const steps = [];
    let current = solutionTerm;
    while (current.indicator === "./2") {
        const head = current.args[0]; // A "move(...)" term
        steps.push(moveToSentence(head, species));
        current = current.args[1];    // Next cell
    }
    return steps;
}

/**
 * Solve the puzzle, returning an array of solutions. Each solution is
 * itself an array of textual lines describing the moves.
 */
export async function solveProblem(config) {
    try {
        const prologProgram = generatePrologCode(config);
        console.log("Generated Prolog program:\n", prologProgram);

        const session = pl.create();

        await new Promise((resolve, reject) => {
            session.consult(prologProgram, {
                success: resolve,
                error: (err) => reject(new Error(`Consult error: ${err}`)),
            });
        });

        console.log("\nSearching for all solutions...");

        const solutions = [];
        await new Promise((resolve, reject) => {
            session.query("solve_solution(Sol).", {
                success: gatherAnswers,
                error: (err) => reject(new Error(`Query error: ${err}`)),
            });

            function gatherAnswers() {
                session.answer({
                    success: function (answer) {
                        if (answer === false) {
                            resolve();
                        } else {
                            const solutionTerm = answer.links["Sol"];
                            const steps = solutionToHumanReadableList(solutionTerm, config.species);
                            solutions.push(steps);
                            gatherAnswers();
                        }
                    },
                    fail: function () {
                        resolve();
                    },
                    error: function (err) {
                        reject(new Error(`Answer error: ${err}`));
                    },
                });
            }
        });

        if (solutions.length === 0) {
            console.log("No solution found.");
        } else {
            console.log(`All solutions found. Total: ${solutions.length}\n`);
            solutions.forEach((sol, i) => {
                console.log(`Solution #${i + 1}:`);
                sol.forEach((line) => console.log("  " + line));
                console.log("");
            });
        }

        // Return them for consumption in the caller
        return solutions;
    } catch (error) {
        console.error("Error solving problem:", error);
        throw error;
    }
}

export async function checkUserSolution(prologProgram, config, solutionLines) {
    const stepsArray = parseSolutionLines(config, solutionLines);
    const stepsPrologList = "[" + stepsArray.map(stepToPrologTerm).join(",") + "]";
    const session = pl.create();

    await new Promise((resolve, reject) => {
        session.consult(prologProgram, {
            success: resolve,
            error: (err) => reject(new Error("Consult error: " + err)),
        });
    });

    const query = `
        initial_state(Init),
        check_solution(${stepsPrologList}, Init).
    `;

    let isValid = false;
    await new Promise((resolve, reject) => {
        session.query(query, {
            success: () => getAnswer(),
            error: (err) => reject(new Error("Query error: " + err)),
        });

        function getAnswer() {
            session.answer({
                success: function(answer) {
                    if (answer === false) {
                        resolve();
                    } else {
                        isValid = true;
                        resolve();
                    }
                },
                fail: function() {
                    resolve();
                },
                error: function(err) {
                    reject(new Error("Answer error: " + err));
                }
            });
        }
    });

    return isValid;
}

function parseSolutionLines(config, solutionLines) {
    const speciesNames = config.species.map((s) => s.name);
    const steps = [];

    for (const line of solutionLines) {
        const [leftPart, rightPart] = line.split(" cross ");
        if (!rightPart) {
            throw new Error(`Invalid line (missing ' cross '): ${line}`);
        }

        const directionStr = rightPart.trim();
        let direction;
        if (directionStr === "left -> right") {
            direction = "leftToRight";
        } else if (directionStr === "right -> left") {
            direction = "rightToLeft";
        } else {
            throw new Error(`Invalid direction segment in line: ${line}`);
        }

        const segments = leftPart.split(",");
        const amounts = new Array(speciesNames.length).fill(0);

        for (const segRaw of segments) {
            const seg = segRaw.trim();
            const match = seg.match(/^(\d+)\s+(\S+)$/);
            if (!match) {
                throw new Error(`Cannot parse segment "${seg}" in line: ${line}`);
            }
            const count = parseInt(match[1], 10);
            const spName = match[2];
            const idx = speciesNames.indexOf(spName);
            if (idx < 0) {
                throw new Error(`Unknown species "${spName}" in line: ${line}`);
            }
            amounts[idx] += count;
        }

        steps.push({ amounts, direction });
    }

    return steps;
}

/**
 * Convert one step object like { amounts: [2,0], direction: 'leftToRight' }
 * into a Prolog term string: step([2,0],leftToRight)
 */
function stepToPrologTerm(stepObj) {
    const { amounts, direction } = stepObj;
    const arrayStr = `[${amounts.join(",")}]`;
    return `step(${arrayStr},${direction})`;
}
