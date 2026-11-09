import { Composition } from "remotion";
import { ShortsComp } from "./ShortsComp";

export const Root = () => {
  return (
    <Composition
      id="ShortsComp"
      component={ShortsComp}
      durationInFrames={30 * 45}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        audioUrl: "",
        images: [] as string[],
        words: [] as Array<{ word: string; start: number; end: number }>,
        durationInSeconds: 45,
      }}
    />
  );
};