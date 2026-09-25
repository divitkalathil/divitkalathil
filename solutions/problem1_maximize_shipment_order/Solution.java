import java.io.*;
import java.util.*;

public class Solution {

    // See solution.py for the reasoning behind the algorithm.
    public static List<Integer> maximizeShipmentOrder(List<Integer> shipmentOrder, int windowSize) {
        int n = shipmentOrder.size();
        int k = windowSize;
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = shipmentOrder.get(i);

        int[] nse = new int[n];
        Arrays.fill(nse, n);
        int[] stack = new int[n];
        int top = 0;
        for (int i = 0; i < n; i++) {
            while (top > 0 && a[stack[top - 1]] > a[i]) nse[stack[--top]] = i;
            stack[top++] = i;
        }

        List<List<Integer>> byNse = new ArrayList<>(n + 1);
        for (int i = 0; i <= n; i++) byNse.add(new ArrayList<>());
        for (int t = 0; t < n; t++) byNse.get(nse[t]).add(t);

        PriorityQueue<Integer> heap = new PriorityQueue<>();
        for (int e = 0; e < k - 1; e++) heap.addAll(byNse.get(e));

        int bestI = -1, bestD = -1;
        boolean alreadySorted = false;
        for (int i = 0; i + k <= n; i++) {
            heap.addAll(byNse.get(i + k - 1));
            while (!heap.isEmpty() && heap.peek() < i) heap.poll();
            if (heap.isEmpty()) {
                alreadySorted = true;
                break;
            }
            int d = heap.peek();
            if (d > bestD) {
                bestD = d;
                bestI = i;
            }
        }

        if (!alreadySorted) Arrays.sort(a, bestI, bestI + k);

        List<Integer> result = new ArrayList<>(n);
        for (int v : a) result.add(v);
        return result;
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StreamTokenizer in = new StreamTokenizer(br);
        in.nextToken();
        int n = (int) in.nval;
        List<Integer> order = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            in.nextToken();
            order.add((int) in.nval);
        }
        in.nextToken();
        int windowSize = (int) in.nval;

        StringBuilder sb = new StringBuilder();
        for (int v : maximizeShipmentOrder(order, windowSize)) sb.append(v).append('\n');
        System.out.print(sb);
    }
}
