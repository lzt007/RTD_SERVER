// Shell-side real MotionEvent injection. This class does not access game state.
// Compile with javac, then Android d8 to a dex; push the dex to /data/local/tmp.
// Run: CLASSPATH=/data/local/tmp/rtd-input.dex app_process /system/bin RTDInput x1 y1 x2 y2 ...
import java.lang.reflect.Method;

public class RTDInput {
    public static void main(String[] args) throws Exception {
        if (args.length < 2 || args.length % 2 != 0) {
            throw new IllegalArgumentException("Expected one or more x/y coordinate pairs");
        }
        float[] coordinates = new float[args.length];
        for (int i = 0; i < args.length; i++) {
            coordinates[i] = Float.parseFloat(args[i]);
            if (Float.isNaN(coordinates[i]) || Float.isInfinite(coordinates[i]) || coordinates[i] < 0) {
                throw new IllegalArgumentException("Coordinates must be finite and nonnegative");
            }
        }
        Class<?> motion = Class.forName("android.view.MotionEvent");
        Class<?> event = Class.forName("android.view.InputEvent");
        Class<?> manager = Class.forName("android.hardware.input.InputManager");
        Object input = manager.getMethod("getInstance").invoke(null);
        Method inject = manager.getMethod("injectInputEvent", event, int.class);
        Method obtain = motion.getMethod("obtain", long.class, long.class, int.class,
                float.class, float.class, int.class);
        Method clock = Class.forName("android.os.SystemClock").getMethod("uptimeMillis");
        long down = ((Long) clock.invoke(null)).longValue();
        float previousX = coordinates[0], previousY = coordinates[1];
        for (int i = 0; i < coordinates.length / 2; i++) {
            float x = coordinates[i * 2], y = coordinates[i * 2 + 1];
            int steps = i == 0 ? 1 : 8;
            for (int step = 1; step <= steps; step++) {
                Object motionEvent = obtain.invoke(null, down, clock.invoke(null), i == 0 ? 0 : 2,
                        previousX + (x - previousX) * step / steps,
                        previousY + (y - previousY) * step / steps, 0);
                motion.getMethod("setSource", int.class).invoke(motionEvent, 0x1002);
                inject.invoke(input, motionEvent, 2);
                motion.getMethod("recycle").invoke(motionEvent);
                Thread.sleep(35);
            }
            previousX = x;
            previousY = y;
        }
        Object up = obtain.invoke(null, down, clock.invoke(null), 1, previousX, previousY, 0);
        motion.getMethod("setSource", int.class).invoke(up, 0x1002);
        inject.invoke(input, up, 2);
        motion.getMethod("recycle").invoke(up);
    }
}
