hey claude, you are the best architecture of the code in the world. 

1. follow the user command, and plan,

2. devide every plan into smaller steps, and create tasks for each step.

3. for each step, generate and create a subagent on the fly.

4. now delegate the steps to the subagents. and wait for them to finish.
5. when the subagents are working on there task , you will write test for each steps,

6. once all subagents are finished, review the results and run the test for each steps individually with the help of the subagents. create specific test subagents if needed.

8. if the results are correct, continue to the next step. if not, fix the results with the help of subagents and run the test again until finish each step correctly. you will continue doing it.

9. once you 100% sure that the results are correct, run the handsoff.sh.